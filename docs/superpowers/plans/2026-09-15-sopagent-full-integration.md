# SopAgent Full Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the business behavior present in SopAgent inside FastStack and make the complete S&OP module available to every authenticated user on existing and new databases.

**Architecture:** Add a dedicated, idempotent S&OP menu reconciler keyed by stable route names and permission strings, then enforce the reconciled menu set as mandatory for every role. Restore the old UI by porting its pure business transformations into tested TypeScript utilities and composing focused Element Plus components around the current `/api/v1/sop/*` API rather than copying the old shell or authentication code.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async/sync, pytest, Vue 3.5, TypeScript 6, Element Plus 2.14, ECharts 6, Vitest 4, SSE/fetch.

**Spec:** `docs/superpowers/specs/2026-09-15-sopagent-full-integration-design.md`

## Global Constraints

- Keep FastStack authentication, users, roles, dynamic routes, and operation auditing.
- Every authenticated user receives every S&OP query and mutation permission.
- Existing databases and user data must be upgraded in place; clearing Docker volumes is forbidden.
- Keep the current Vue/TypeScript/Element Plus application shell; do not embed the old frontend.
- Render only real API data. Missing facts use explicit empty states and never demo fallbacks.
- Do not change menus, roles, or pages outside the S&OP integration except for the narrowly required role-service hook.
- Preserve the user's existing uncommitted integration work and commit only files belonging to each task.

---

### Task 1: Idempotent S&OP Menu Reconciliation

**Files:**
- Create: `backend/app/modules/sop/menu_sync.py`
- Create: `backend/tests/module_sop/test_menu_sync.py`
- Modify: `backend/app/scripts/initialize.py`
- Modify: `backend/sql/sys_role_menus.json`

**Interfaces:**
- Produces: `SOP_MENU_TREE: tuple[SopMenuDefinition, ...]`.
- Produces: `async reconcile_sop_menus(db: AsyncSession) -> set[int]`, returning every reconciled S&OP menu ID.
- Produces: `async grant_sop_menus_to_all_roles(db: AsyncSession, menu_ids: set[int]) -> None`.
- Consumes: `MenuModel`, `RoleModel`, and `RoleMenusModel` from the system module.

- [ ] **Step 1: Read the test-writing rules and add a failing reconciliation test**

Read `skills/test-driven-development/writing-good-tests.md`, then create a test which inserts an unrelated menu and role into the isolated test database, calls the intended reconciler twice, and asserts stable keys, parent relationships, unchanged unrelated data, full role coverage, and no duplicate `sys_role_menus` rows:

```python
@pytest.mark.asyncio
async def test_reconcile_sop_menus_is_idempotent_and_grants_all_roles(db_session):
    unrelated = MenuModel(name="保留菜单", type=2, route_name="KeepMe", route_path="/keep")
    role = RoleModel(name="业务用户", code="BIZ", order=9, status=0, data_scope=1)
    db_session.add_all([unrelated, role])
    await db_session.flush()

    first = await reconcile_sop_menus(db_session)
    second = await reconcile_sop_menus(db_session)

    assert first == second
    assert len(first) == 16
    assert (await db_session.scalar(select(func.count()).where(MenuModel.route_name == "KeepMe"))) == 1
    links = (await db_session.scalars(select(RoleMenusModel.menu_id).where(RoleMenusModel.role_id == role.id))).all()
    assert set(links) == first
    assert len(links) == len(set(links))
```

- [ ] **Step 2: Run the focused test and verify the expected red state**

Run: `cd backend && uv run pytest tests/module_sop/test_menu_sync.py -q`

Expected: collection fails because `app.modules.sop.menu_sync` does not exist.

- [ ] **Step 3: Implement stable menu definitions and recursive upsert**

Define an immutable dataclass with the actual managed columns:

```python
@dataclass(frozen=True, slots=True)
class SopMenuDefinition:
    key: str
    name: str
    type: int
    order: int
    permission: str | None = None
    route_name: str | None = None
    route_path: str | None = None
    component_path: str | None = None
    icon: str | None = None
    redirect: str | None = None
    description: str | None = None
    children: tuple["SopMenuDefinition", ...] = ()
```

Use `route_name` for the directory/page lookup and `permission` for button lookup. For each definition, select an existing row, create it if absent, update only S&OP-managed display/routing fields, flush to obtain its real ID, and recurse with that ID as `parent_id`. Include one distinct `module_sop:data:sync` button instead of duplicating `module_sop:data:import` for the sync action.

- [ ] **Step 4: Implement additive role grants without fixed IDs**

Select every non-deleted `RoleModel.id`, select existing pairs for the returned menu IDs, and add only missing `RoleMenusModel(role_id=..., menu_id=...)` pairs. Do not clear role menus. Remove the stale fixed-ID entries from `backend/sql/sys_role_menus.json`; the reconciler becomes the sole S&OP grant source.

- [ ] **Step 5: Attach reconciliation to database initialization**

At the end of `InitializeData.__init_data`, after base tables and seed rows exist, call:

```python
menu_ids = await reconcile_sop_menus(db)
await grant_sop_menus_to_all_roles(db, menu_ids)
```

Let exceptions propagate so startup cannot silently succeed with an inaccessible module.

- [ ] **Step 6: Run the focused and initialization regression tests**

Run: `cd backend && uv run pytest tests/module_sop/test_menu_sync.py tests/test_migrations.py -q`

Expected: all selected tests pass and a second reconciliation creates no additional rows.

- [ ] **Step 7: Commit the permission reconciler**

```bash
git add backend/app/modules/sop/menu_sync.py backend/tests/module_sop/test_menu_sync.py backend/app/scripts/initialize.py backend/sql/sys_role_menus.json
git commit -m "fix: reconcile Sop menus and role grants"
```

### Task 2: Make S&OP Permissions Mandatory for New and Edited Roles

**Files:**
- Modify: `backend/app/modules/sop/menu_sync.py`
- Modify: `backend/app/modules/system/role/service.py`
- Modify: `backend/tests/module_sop/test_menu_sync.py`
- Modify: `backend/tests/module_sop/test_sop_routes.py`

**Interfaces:**
- Consumes: `async get_sop_menu_ids(db: AsyncSession) -> set[int]` from `menu_sync.py`.
- Produces: role creation and permission replacement behavior that always includes the complete S&OP ID set.

- [ ] **Step 1: Add failing tests for role creation and permission replacement**

Test the real service behavior with persisted roles:

```python
@pytest.mark.asyncio
async def test_setting_role_permissions_cannot_remove_sop(db_session, auth):
    sop_ids = await reconcile_sop_menus(db_session)
    role = RoleModel(name="受限角色", code="LIMITED", order=10, status=0, data_scope=1)
    db_session.add(role)
    await db_session.flush()

    await RoleService(auth, db_session)._set_role_menus([role.id], [])
    await db_session.refresh(role, attribute_names=["menus"])

    assert sop_ids <= {menu.id for menu in role.menus}
```

Add an API regression that logs in as the non-superuser `user` fixture and requests one query route and one mutation route; assert neither response is HTTP 403.

- [ ] **Step 2: Run the tests and verify they fail because replacement clears required menus**

Run: `cd backend && uv run pytest tests/module_sop/test_menu_sync.py tests/module_sop/test_sop_routes.py -q`

Expected: the role service test shows an empty S&OP menu intersection, or the regular user receives HTTP 403.

- [ ] **Step 3: Union mandatory IDs in role service paths**

Add `get_sop_menu_ids` to query the reconciled stable keys. In `RoleService._set_role_menus`, replace the requested ID set with:

```python
effective_menu_ids = set(menu_ids)
effective_menu_ids.update(await get_sop_menu_ids(self.db))
```

Validate and persist `effective_menu_ids`. In `RoleService.create`, assign the mandatory menu objects to the newly created role after `RoleCRUD.create` and before returning detail.

- [ ] **Step 4: Give warehouse sync its distinct permission**

Change the warehouse sync controller guard from `module_sop:data:import` to `module_sop:data:sync`, matching the manifest. Update route tests to enumerate every controller permission and assert the regular user token contains all of them after a fresh login.

- [ ] **Step 5: Run role, route, auth, and initialization tests**

Run: `cd backend && uv run pytest tests/module_sop/test_menu_sync.py tests/module_sop/test_sop_routes.py tests/test_main.py tests/test_migrations.py -q`

Expected: all selected tests pass.

- [ ] **Step 6: Commit mandatory permission behavior**

```bash
git add backend/app/modules/sop/menu_sync.py backend/app/modules/system/role/service.py backend/app/modules/sop/data/controller.py backend/tests/module_sop/test_menu_sync.py backend/tests/module_sop/test_sop_routes.py
git commit -m "fix: keep Sop permissions for every role"
```

### Task 3: Port and Test Shared S&OP Presentation Logic

**Files:**
- Create: `frontend/web/src/views/module_sop/shared/presentation.ts`
- Create: `frontend/web/src/views/module_sop/shared/report-metrics.ts`
- Create: `frontend/web/src/views/module_sop/shared/report-data.ts`
- Create: `frontend/web/src/views/module_sop/shared/__tests__/presentation.spec.ts`
- Create: `frontend/web/src/views/module_sop/shared/__tests__/report-data.spec.ts`
- Modify: `frontend/web/src/api/module_sop/types.ts`

**Interfaces:**
- Produces: `formatOptional`, `buildKnowledgeMetrics`, `getFilePresentation`, `buildForecastValidationSummary`, and `buildSourceContext`.
- Produces: `buildReportMetrics`, `buildMaterialList`, `buildDecisionSummary`, `getSourceSyncDisplay`, `getReportReadinessDisplay`, and `getOverallDataStatusDisplay`.
- Produces: `buildTrendChartDataset(report: SopFirstPhaseReport | null): SopTrendPoint[]` and `buildChannelForecastMatrix(report: SopFirstPhaseReport | null): SopChannelMatrix`.

- [ ] **Step 1: Port the original pure-function tests before production utilities**

Translate the assertions from `../SopAgent/frontend/tests/presentation.test.js` and `reportMetrics.test.js` to Vitest/TypeScript. Add cases proving `null` remains `—`, numeric zero remains zero, a null report produces no sample facts, and forecast matrices are derived only from the selected report.

```ts
it("does not synthesize business facts for an empty report", () => {
  expect(buildTrendChartDataset(null)).toEqual([]);
  expect(buildChannelForecastMatrix(null)).toEqual({
    months: [], channels: [], submitMatrix: {}, aiBaselineMatrix: {}, deviationMatrix: {}, diffList: [],
  });
});
```

- [ ] **Step 2: Run the new tests and verify imports fail**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/shared/__tests__`

Expected: FAIL because the three utility modules do not exist.

- [ ] **Step 3: Port the minimal pure implementations and add strict types**

Port the business calculations from the old `presentation.js` and `reportMetrics.js`, excluding `OFFICIAL_SOP_TREND_DEMO`. Define `SopTrendPoint`, `SopChannelMatrix`, `SopChannelDifference`, and document metadata types in `types.ts`; do not use `any` for report payloads consumed by pages.

- [ ] **Step 4: Run utility tests and type checking**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/shared/__tests__ && pnpm type-check`

Expected: tests pass and Vue TypeScript reports zero errors.

- [ ] **Step 5: Commit shared presentation logic**

```bash
git add frontend/web/src/views/module_sop/shared frontend/web/src/api/module_sop/types.ts
git commit -m "feat: restore tested Sop report calculations"
```

### Task 4: Restore the Shared Trend Chart and Dashboard

**Files:**
- Create: `frontend/web/src/views/module_sop/shared/SopTrendChart.vue`
- Create: `frontend/web/src/views/module_sop/dashboard/__tests__/dashboard.spec.ts`
- Modify: `frontend/web/src/views/module_sop/dashboard/index.vue`

**Interfaces:**
- Consumes: `SopTrendPoint[]` and `SopChannelMatrix` from Task 3.
- Produces: reusable `<SopTrendChart :data="trendData" />`.

- [ ] **Step 1: Add a failing dashboard component test**

Mock `SopDataAPI`, `SopDocumentAPI`, and `SopReportAPI` with real response-shaped values, mount the dashboard, and assert it renders the readiness banner, document/snapshot metrics, trend section, channel matrix headings, and empty-state copy when report facts are absent.

- [ ] **Step 2: Run the dashboard test and verify the missing sections fail**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/dashboard/__tests__/dashboard.spec.ts`

Expected: FAIL because the current dashboard has no trend or channel matrix sections.

- [ ] **Step 3: Implement a lifecycle-safe trend chart**

Wrap ECharts in a focused component. Initialize on mount, call `setOption` when the `data` prop changes, resize through `ResizeObserver`, and dispose both observer and chart on unmount. Plot outbound, activation, AI baseline, and submitted forecast as distinct series; event annotations come only from input data.

- [ ] **Step 4: Restore dashboard content with real data**

Load data status, documents, snapshots, SPUs, and the first available SPU report concurrently where dependencies allow. Use Task 3 helpers for every metric and matrix. Show Element Plus skeleton/error/empty states and provide a retry action; do not embed sample quantities.

- [ ] **Step 5: Run dashboard tests, type check, and build**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/dashboard/__tests__/dashboard.spec.ts src/views/module_sop/shared/__tests__ && pnpm type-check && pnpm build`

Expected: all commands exit 0.

- [ ] **Step 6: Commit dashboard restoration**

```bash
git add frontend/web/src/views/module_sop/shared/SopTrendChart.vue frontend/web/src/views/module_sop/dashboard
git commit -m "feat: restore Sop dashboard analytics"
```

### Task 5: Restore Data Center Workflows

**Files:**
- Modify: `frontend/web/src/api/module_sop/data.ts`
- Modify: `frontend/web/src/views/module_sop/data_center/index.vue`
- Create: `frontend/web/src/views/module_sop/data_center/__tests__/data-center.spec.ts`

**Interfaces:**
- Consumes: current status/import/sync endpoints and `getSourceSyncDisplay` from Task 3.
- Produces: one page containing source status, imports, SPU dictionary, validation policy, snapshot policy, and snapshot history.

- [ ] **Step 1: Add a failing page test for the five business sections**

Mock nine source domains and two snapshots. Assert the page shows source labels, business date, record count, the four import actions, warehouse sync, SPU dictionary, validation policy, snapshot policy, and snapshot history.

- [ ] **Step 2: Run the test and verify the simplified page fails the assertions**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/data_center/__tests__/data-center.spec.ts`

Expected: FAIL on the missing dictionary, policy, and snapshot sections.

- [ ] **Step 3: Complete API methods needed by the page**

Ensure `data.ts` exposes typed methods for status, paged SPU lookup, all four import types, and warehouse sync. Reuse `SopReportAPI.getSnapshotList` for history rather than adding a duplicate backend endpoint.

- [ ] **Step 4: Restore the page and operation feedback**

Use tabs or vertically separated cards to preserve the old information architecture. After import or sync, reload statuses and snapshots. Render accepted/rejected counts and quality issue IDs from the server. Disable only the operation currently running and allow unrelated read interactions.

- [ ] **Step 5: Verify and commit the data center**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/data_center/__tests__/data-center.spec.ts src/views/module_sop/shared/__tests__ && pnpm type-check`

```bash
git add frontend/web/src/api/module_sop/data.ts frontend/web/src/views/module_sop/data_center
git commit -m "feat: restore Sop data center workflows"
```

### Task 6: Restore Knowledge Document Details and Batch Upload

**Files:**
- Modify: `backend/app/modules/sop/document/controller.py`
- Modify: `backend/app/modules/sop/services/parent_chunk_store.py`
- Modify: `backend/app/modules/sop/schemas/document.py`
- Modify: `backend/tests/module_sop/test_sop_routes.py`
- Modify: `frontend/web/src/api/module_sop/document.ts`
- Modify: `frontend/web/src/api/module_sop/types.ts`
- Modify: `frontend/web/src/views/module_sop/knowledge/index.vue`
- Create: `frontend/web/src/views/module_sop/knowledge/__tests__/knowledge.spec.ts`

**Interfaces:**
- Produces: `GET /api/v1/sop/documents/{filename}/chunks` returning persisted chunk previews owned by the named document.
- Produces: typed `SopDocumentChunk` and `SopDocumentAPI.getChunks(filename)`.
- Consumes: existing batch-upload and document delete services.

- [ ] **Step 1: Add failing backend and frontend tests**

Backend: persist parent chunks for two filenames, request one filename, and assert only its chunks are returned and authentication is required. Frontend: mount with two documents and assert metrics, type badges, batch upload, refresh, chunk drawer, deletion, and backend error text are present.

- [ ] **Step 2: Run focused tests and verify the missing chunk API/UI fail**

Run: `cd backend && uv run pytest tests/module_sop/test_sop_routes.py -q`

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/knowledge/__tests__/knowledge.spec.ts`

Expected: backend returns 404 for the chunk route and frontend lacks the chunk drawer.

- [ ] **Step 3: Add the smallest persisted-chunk query endpoint**

Add a store method filtering by document metadata/filename and returning chunk ID, ordinal, content preview, and metadata. Add a read-only controller guarded by `module_sop:document:query`. Do not query Milvus when the relational parent-chunk store already owns this data.

- [ ] **Step 4: Restore typed batch upload and knowledge UI**

Expose `batchUpload(files: File[])` and `getChunks(filename)` in the API module. Restore document/chunk metrics, file presentation, multi-file upload, refresh, a chunk drawer, deletion confirmation, and processing errors using Element Plus.

- [ ] **Step 5: Verify and commit knowledge restoration**

Run: `cd backend && uv run pytest tests/module_sop/test_sop_routes.py -q`

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/knowledge/__tests__/knowledge.spec.ts src/views/module_sop/shared/__tests__/presentation.spec.ts && pnpm type-check`

```bash
git add backend/app/modules/sop/document backend/app/modules/sop/services/parent_chunk_store.py backend/app/modules/sop/schemas/document.py backend/tests/module_sop/test_sop_routes.py frontend/web/src/api/module_sop/document.ts frontend/web/src/api/module_sop/types.ts frontend/web/src/views/module_sop/knowledge
git commit -m "feat: restore Sop knowledge workflows"
```

### Task 7: Make Chat Streaming Correct and Restore Chat Details

**Files:**
- Create: `frontend/web/src/api/module_sop/sse.ts`
- Create: `frontend/web/src/api/module_sop/__tests__/sse.spec.ts`
- Modify: `frontend/web/src/api/module_sop/chat.ts`
- Modify: `frontend/web/src/views/module_sop/chat/index.vue`
- Create: `frontend/web/src/views/module_sop/chat/__tests__/chat.spec.ts`

**Interfaces:**
- Produces: `parseSseStream(stream: ReadableStream<Uint8Array>, handlers: ChatStreamHandlers, signal?: AbortSignal): Promise<void>`.
- Produces: `streamChat(..., signal?: AbortSignal): Promise<void>` with exactly-once completion.
- Consumes: DOMPurify, markdown-it, and highlight.js already present in the frontend.

- [ ] **Step 1: Add failing SSE parser tests**

Cover frames split across byte chunks, CRLF separators, multiple `data:` lines, `[DONE]`, malformed heartbeat data, server error events, abort, and a final frame without a trailing blank line. Assert `onDone` fires exactly once.

- [ ] **Step 2: Run the parser test and verify the current inline parser fails edge cases**

Run: `cd frontend/web && pnpm vitest run src/api/module_sop/__tests__/sse.spec.ts`

Expected: FAIL because `parseSseStream` does not exist.

- [ ] **Step 3: Implement the standalone parser and AbortSignal support**

Keep a decoded buffer, normalize CRLF, dispatch complete frames, flush the decoder and remaining buffer at EOF, stop dispatch after `[DONE]`, and centralize exactly-once finalization. Pass `signal` into fetch and cancel the reader on abort.

- [ ] **Step 4: Add failing chat component behavior tests**

Assert session load/switch/delete, disabled send while streaming, progressive assistant content, RAG step/trace display, sanitized Markdown, user-visible stream errors, and cancellation on component unmount.

- [ ] **Step 5: Restore the chat page behavior**

Move Markdown setup to a focused helper or the component's module scope. Preserve session ownership on the backend. Add retryable error state and abort the active request before starting a new session, switching sessions, or unmounting.

- [ ] **Step 6: Verify and commit chat restoration**

Run: `cd frontend/web && pnpm vitest run src/api/module_sop/__tests__/sse.spec.ts src/views/module_sop/chat/__tests__/chat.spec.ts && pnpm type-check`

```bash
git add frontend/web/src/api/module_sop/sse.ts frontend/web/src/api/module_sop/__tests__/sse.spec.ts frontend/web/src/api/module_sop/chat.ts frontend/web/src/views/module_sop/chat
git commit -m "fix: restore reliable Sop streaming chat"
```

### Task 8: Restore Analysis and Full Meeting Report

**Files:**
- Create: `frontend/web/src/views/module_sop/shared/ChannelForecastMatrix.vue`
- Create: `frontend/web/src/views/module_sop/shared/ForecastValidationTable.vue`
- Modify: `frontend/web/src/views/module_sop/analysis/index.vue`
- Modify: `frontend/web/src/views/module_sop/report/index.vue`
- Create: `frontend/web/src/views/module_sop/analysis/__tests__/analysis.spec.ts`
- Create: `frontend/web/src/views/module_sop/report/__tests__/report.spec.ts`

**Interfaces:**
- Consumes: Task 3 report helpers and Task 4 `SopTrendChart`.
- Produces: reusable channel matrix and validation table components shared by analysis/report pages.

- [ ] **Step 1: Add failing tests for restored report semantics**

Analysis assertions: SPU search, dimension filters, trend, validation summary, evidence table, level labels, rule version, and export. Report assertions: readiness, metrics, materials, snapshots, trend, channel matrix, difference list, factual decision summary, snapshot generation/detail, and Word export.

- [ ] **Step 2: Run tests and verify the current shortened pages fail**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/analysis/__tests__/analysis.spec.ts src/views/module_sop/report/__tests__/report.spec.ts`

Expected: FAIL on the missing report sections and interactions.

- [ ] **Step 3: Implement shared matrix and validation components**

The matrix receives a fully built `SopChannelMatrix` and renders submitted quantity, AI baseline, and deviation without recomputing business rules. The validation table receives `SopForecastCheck[]`, uses `buildForecastValidationRows`, and shows non-evaluable records distinctly from low/medium/high outcomes.

- [ ] **Step 4: Restore analysis page composition**

Retain its existing SPU/dimension query flow, replace local ad-hoc calculations with shared helpers, and compose the trend plus validation components. Reset stale report state when SPU or filters change and preserve zero values.

- [ ] **Step 5: Restore report page composition and download behavior**

Compose every report section from the current report or selected immutable snapshot. Use a blob request for Word export and a deterministic filename containing SPU and as-of date. After generation, refresh history and select the newly generated snapshot when returned.

- [ ] **Step 6: Verify and commit analysis/report restoration**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/analysis/__tests__/analysis.spec.ts src/views/module_sop/report/__tests__/report.spec.ts src/views/module_sop/shared/__tests__ && pnpm type-check && pnpm build`

```bash
git add frontend/web/src/views/module_sop/shared frontend/web/src/views/module_sop/analysis frontend/web/src/views/module_sop/report
git commit -m "feat: restore Sop analysis and meeting reports"
```

### Task 9: Restore Market Empty State and Audit Original-to-New Parity

**Files:**
- Modify: `frontend/web/src/views/module_sop/market/index.vue`
- Create: `frontend/web/src/views/module_sop/market/__tests__/market.spec.ts`
- Create: `docs/sopagent-parity.md`
- Modify: any `backend/app/modules/sop/**` or `frontend/web/src/{api,views}/module_sop/**` file only when the parity audit proves a concrete original capability is still missing.

**Interfaces:**
- Produces: an auditable mapping from every original page/API/domain capability to its SopFast location and verification.

- [ ] **Step 1: Add a failing market-state test**

Assert configured records render with source and timestamp, while HTTP 404/unconfigured responses show the original capability description and auditability principles rather than a generic error toast.

- [ ] **Step 2: Run the market test and verify configured rendering is absent**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/market/__tests__/market.spec.ts`

Expected: FAIL because the current page always treats the endpoint as unavailable.

- [ ] **Step 3: Implement truthful market rendering**

Normalize an empty/unconfigured response into a stable empty-state model. Render records only if returned by the API, including their source and observation timestamp. Do not add a provider or bundled sample data.

- [ ] **Step 4: Complete the parity matrix**

Inventory `../SopAgent/backend/app`, `../SopAgent/frontend/src/components/sop`, its services, and tests. For each original capability, record `restored`, `replaced by FastStack`, or `intentionally excluded by spec`, with the exact current file and test command. A capability cannot be marked restored based only on file presence.

- [ ] **Step 5: Resolve only proven parity gaps using another red-green cycle**

For each uncovered in-scope gap, add one focused failing test, run it to observe the expected failure, implement the smallest correction, and rerun the focused test. Record the test in `docs/sopagent-parity.md`.

- [ ] **Step 6: Verify and commit market/parity work**

Run: `cd frontend/web && pnpm vitest run src/views/module_sop/market/__tests__/market.spec.ts && pnpm type-check`

Run: `cd backend && uv run pytest tests/module_sop -q`

```bash
git add frontend/web/src/views/module_sop/market docs/sopagent-parity.md backend/app/modules/sop backend/tests/module_sop frontend/web/src/api/module_sop frontend/web/src/views/module_sop
git commit -m "docs: verify SopAgent integration parity"
```

### Task 10: Upgrade the Existing Database and Perform Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/sopagent-parity.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified existing-volume upgrade and operator instructions.

- [ ] **Step 1: Capture pre-upgrade counts without changing data**

Query `sys_menu`, `sys_role`, `sys_role_menus`, and all S&OP business tables. Record counts locally for comparison; do not put credentials or private business rows into documentation.

- [ ] **Step 2: Restart the backend against the existing volume**

Use the repository's normal `run.sh`/backend command. Confirm logs show S&OP reconciliation and no migration, MCP, scheduler, or import traceback.

- [ ] **Step 3: Verify database invariants after reconciliation**

Run read-only queries proving every active role has exactly the complete S&OP ID set, menu stable keys are unique, parent IDs are correct, unrelated row counts remain unchanged, and a second restart leaves counts unchanged.

- [ ] **Step 4: Verify all three built-in users through HTTP**

Log in as `super`, `admin`, and `user`, fetch the current-user/menu response, and assert all seven route names are returned. With `user`, call one endpoint for every S&OP permission and verify none returns HTTP 401/403. Avoid printing tokens.

- [ ] **Step 5: Run complete automated verification**

Run: `cd backend && uv run pytest -q`

Run: `cd frontend/web && pnpm test && pnpm type-check && pnpm build`

Expected: every command exits 0 with no failed tests or type/build errors.

- [ ] **Step 6: Perform browser smoke tests for the three main flows**

Use the running local app as regular `user` and verify: document upload → chunk view → chat; data import/sync → dashboard/analysis; snapshot generation → report detail → Word download. Capture screenshots of the seven page states and inspect console/network errors.

- [ ] **Step 7: Document upgrade and token refresh behavior**

Update `README.md` to state that S&OP menus are reconciled on startup for all roles, existing sessions must sign in again after the first upgrade, and external dependencies can independently show degraded states.

- [ ] **Step 8: Commit final verification documentation**

```bash
git add README.md docs/sopagent-parity.md
git commit -m "docs: describe Sop integration upgrade"
```

- [ ] **Step 9: Review the resulting branch**

Run `git status --short`, inspect `git diff` against the pre-integration base without discarding user changes, and use the code-review workflow. Resolve any correctness findings with focused tests before declaring completion.
