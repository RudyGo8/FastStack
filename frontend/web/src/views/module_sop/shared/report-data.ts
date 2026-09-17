import type {
  SopAnnualChannelMatrix,
  SopChannelMatrix,
  SopFirstPhaseReport,
  SopTrendPoint,
} from "@/api/module_sop/types";

const EMPTY_MATRIX: SopChannelMatrix = {
  months: [],
  channels: [],
  submitMatrix: {},
  aiBaselineMatrix: {},
  deviationMatrix: {},
  diffList: [],
};
const SUBMITTED_FORECAST_TYPES = new Set(["sales_submission", "sales_reported", "submit"]);
const REPORT_CHANNELS = [
  "国际渠道销售一部",
  "国际渠道销售二部",
  "海外电商",
  "国内渠道",
  "国内电商",
  "其他",
];
const ROLLUP_CHANNELS = new Set(["ALL", "全部渠道", "全渠道", "全国渠道", "全部"]);
const CHANNEL_ALIASES: Record<string, string> = {
  海外渠道一部: "国际渠道销售一部",
  海外渠道销售一部: "国际渠道销售一部",
  海外渠道二部: "国际渠道销售二部",
  海外渠道销售二部: "国际渠道销售二部",
  海外电商销售部: "海外电商",
  国内渠道销售部: "国内渠道",
  国内电商销售部: "国内电商",
};

function normalizeReportChannel(channel: string): string {
  const value = String(channel || "").trim();
  return CHANNEL_ALIASES[value] || (REPORT_CHANNELS.includes(value) ? value : "其他");
}

function buildEventMap(report: SopFirstPhaseReport | null): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of report?.events ?? []) {
    const month = String(item.event_month || "").slice(0, 7);
    if (month && item.event) map.set(month, item.event);
  }
  return map;
}

export type ReportPeriod = readonly [string, string];

export function forecastMonths(report: SopFirstPhaseReport | null): string[] {
  if (!report) return [];
  const anchor = report.as_of_date.slice(0, 7);
  const [year, month] = anchor.split("-").map(Number);
  return Array.from({ length: 6 }, (_, index) => {
    const offset = (month ?? 1) - 1 + index;
    return `${(year ?? 0) + Math.floor(offset / 12)}-${String((offset % 12) + 1).padStart(2, "0")}`;
  });
}

// Every view uses the same six calendar months, submitted types and latest raw-channel version.
export function submittedForecasts(report: SopFirstPhaseReport | null) {
  if (!report) return [];
  const months = new Set(forecastMonths(report));
  const latest = new Map<string, SopFirstPhaseReport["forecasts"][number]>();
  for (const item of report.forecasts) {
    const month = item.forecast_month.slice(0, 7);
    if (
      !months.has(month) ||
      !SUBMITTED_FORECAST_TYPES.has(item.forecast_type) ||
      String(item.snapshot_at).slice(0, 10) > report.as_of_date.slice(0, 10)
    )
      continue;
    const grain = `${item.region}|${item.channel}|${month}`;
    const previous = latest.get(grain);
    if (
      !previous ||
      `${item.snapshot_at}|${item.version}` > `${previous.snapshot_at}|${previous.version}`
    )
      latest.set(grain, item);
  }
  const values = [...latest.values()];
  const detailed = new Set(
    values
      .filter((item) => !ROLLUP_CHANNELS.has(item.channel.trim()))
      .map((item) => `${item.region}|${item.forecast_month.slice(0, 7)}`)
  );
  return values.filter(
    (item) =>
      !ROLLUP_CHANNELS.has(item.channel.trim()) ||
      !detailed.has(`${item.region}|${item.forecast_month.slice(0, 7)}`)
  );
}

export function reportSyncTime(report: SopFirstPhaseReport | null): string {
  if (report?.source_synced_at) return report.source_synced_at.replace("T", " ");
  const stamps = (report?.provenance ?? [])
    .map((item) => String(item.snapshot_at).replace("T", " "))
    .filter(Boolean)
    .sort();
  return stamps[0] ?? "—";
}

export function buildTrendChartDataset(
  report: SopFirstPhaseReport | null,
  period?: ReportPeriod
): SopTrendPoint[] {
  if (!report) return [];
  const eventMap = buildEventMap(report);
  const [start = "", end = "9999-12"] = period ?? [];
  const timeline = new Map<string, SopTrendPoint>();
  for (const actual of report.monthly_actuals) {
    if (actual.period < start || actual.period > end) continue;
    timeline.set(actual.period, {
      period: actual.period,
      type: "actual",
      outbound_qty: Number(actual.outbound_qty) || 0,
      activation_qty: Number(actual.activation_qty) || 0,
      ai_forecast_outbound: null,
      ai_forecast_activation: null,
      submit_forecast: null,
      event: eventMap.get(actual.period) ?? "",
    });
  }
  for (const item of submittedForecasts(report)) {
    const month = item.forecast_month.slice(0, 7);
    let point = timeline.get(month);
    if (!point) {
      point = {
        period: month,
        type: "forecast",
        outbound_qty: null,
        activation_qty: null,
        ai_forecast_outbound: null,
        ai_forecast_activation: null,
        submit_forecast: null,
        event: eventMap.get(month) ?? "",
      };
      timeline.set(month, point);
    }
    point.submit_forecast = (point.submit_forecast ?? 0) + Number(item.forecast_qty || 0);
  }
  return [...timeline.values()].sort((a, b) => a.period.localeCompare(b.period));
}

export function buildChannelForecastMatrix(report: SopFirstPhaseReport | null): SopChannelMatrix {
  if (!report) return { ...EMPTY_MATRIX };
  const currentMonth = report.as_of_date.slice(0, 7);

  const months = [
    ...new Set(
      report.forecasts
        .map((item) => item.forecast_month.slice(0, 7))
        .filter((m) => m >= currentMonth)
    ),
  ]
    .sort()
    .slice(0, 6);

  const channels = [
    ...new Set(report.forecasts.map((item) => item.channel).filter(Boolean)),
  ].sort();

  if (!months.length || !channels.length) return { ...EMPTY_MATRIX };

  const matrix: SopChannelMatrix = {
    months,
    channels,
    submitMatrix: {},
    aiBaselineMatrix: {},
    deviationMatrix: {},
    diffList: [],
  };

  for (const channel of channels) {
    matrix.submitMatrix[channel] = [];
    for (const month of months) {
      const forecast = report.forecasts.find(
        (item) => item.channel === channel && item.forecast_month.slice(0, 7) === month
      );
      const submit = Number(forecast?.forecast_qty ?? 0) || 0;
      matrix.submitMatrix[channel].push(submit);
    }
  }

  const submitTotals = months.map((_, index) =>
    channels.reduce((sum, channel) => sum + (matrix.submitMatrix[channel]?.[index] ?? 0), 0)
  );
  matrix.submitMatrix["合计"] = submitTotals;

  return matrix;
}

export function buildAnnualChannelMatrix(
  report: SopFirstPhaseReport | null,
  period?: ReportPeriod
): SopAnnualChannelMatrix {
  if (!report) return { year: 0, months: [], salesMonthCount: 0, rows: [] };
  const anchorMonth = report.as_of_date.slice(0, 7);
  const year = Number(anchorMonth.slice(0, 4));
  const [start = `${year}-01`, selectedEnd = anchorMonth] = period ?? [];
  const end = selectedEnd < anchorMonth ? selectedEnd : anchorMonth;
  const actualMonths: string[] = [];
  if (start <= end) {
    const [firstYear = year, firstMonth = 1] = start.split("-").map(Number);
    const [lastYear = year, lastMonth = 1] = end.split("-").map(Number);
    const count = (lastYear - firstYear) * 12 + lastMonth - firstMonth + 1;
    for (let index = 0; index < count; index++) {
      const offset = firstMonth - 1 + index;
      actualMonths.push(
        `${firstYear + Math.floor(offset / 12)}-${String((offset % 12) + 1).padStart(2, "0")}`
      );
    }
  }
  // The actual and forecast groups each include the current month without overwriting one another.
  const predictionMonths = forecastMonths(report);
  const months = [...actualMonths, ...predictionMonths];
  const actuals = new Map<string, number>();
  const activations = new Map<string, number>();
  const forecasts = new Map<string, number>();
  for (const item of report.channel_actuals ?? []) {
    if (ROLLUP_CHANNELS.has(String(item.channel || "").trim())) continue;
    const key = `${normalizeReportChannel(item.channel)}|${item.period}`;
    actuals.set(key, (actuals.get(key) ?? 0) + Number(item.outbound_qty || 0));
    activations.set(key, (activations.get(key) ?? 0) + Number(item.activation_qty || 0));
  }
  for (const item of submittedForecasts(report)) {
    if (ROLLUP_CHANNELS.has(String(item.channel || "").trim())) continue;
    const key = `${normalizeReportChannel(item.channel)}|${item.forecast_month.slice(0, 7)}`;
    forecasts.set(key, (forecasts.get(key) ?? 0) + Number(item.forecast_qty || 0));
  }
  const rows = REPORT_CHANNELS.map((channel) => ({
    channel,
    outboundOrForecast: [
      ...actualMonths.map((month) => actuals.get(`${channel}|${month}`) ?? null),
      ...predictionMonths.map((month) => forecasts.get(`${channel}|${month}`) ?? null),
    ],
    activations: [
      ...actualMonths.map((month) => activations.get(`${channel}|${month}`) ?? null),
      ...predictionMonths.map(() => null),
    ],
  }));
  return { year, months, salesMonthCount: actualMonths.length, rows };
}
