"""S&OP 数据清单标准数仓 SQL 库 (来自 docs/sop数据清单.xlsx).

遵循架构约束:
1. 白名单固定 SQL，禁止 LLM 自由拼凑 SQL。
2. 包含 Excel 中给出的完整激活大 SQL 与出库、预测、SPU、库存等标准抽取语句。
"""

# 1. 激活数据标准抽取 SQL (来自 sop数据清单.xlsx 第 9 项: 良发提供的数仓脚本)
ACTIVATION_ETL_SQL = """
WITH base_data AS (
    SELECT
        ARE_T_1_.SN,
        ANO_T_4_.name AS product_name,
        A98_T_5_.contry,
        ALA_T_3_.material_name,
        AST_T_2_.events_date,
        ARE_T_1_.testat,
        AEC_T_11_.device_status,
        ARE_T_1_.active_at,
        ARE_T_1_.passed,
        AST_T_2_.events_name,
        A98_T_5_.FBillNo,
        ATN_T_6_.department_name,
        AWE_T_7_.department_one_name,
        AWE_T_7_.department_two_name,
        AWE_T_7_.department_three_name,
        AOF_T_8_.sale_name,
        IF( ARE_T_10_.customer_name is not null,
            ARE_T_10_.customer_name,
            IF( AST_T_2_.events_name = '直接调拨',
                CASE
                    WHEN AKC_T_9_.stock_name LIKE '%速卖通%' OR AKC_T_9_.stock_name LIKE '%优选仓%' OR AKC_T_9_.stock_name LIKE '%保税仓%' THEN '速卖通客户'
                    WHEN AKC_T_9_.stock_name LIKE '%亚马逊%' OR AKC_T_9_.stock_name LIKE '%Amazon%' THEN '亚马逊客户'
                    WHEN AKC_T_9_.stock_name LIKE '%Lazada%' OR AKC_T_9_.stock_name LIKE '%shopee%' THEN '平台客户'
                    WHEN AKC_T_9_.stock_name = '大森林美国海外仓' THEN '海外独立站客户'
                    WHEN AKC_T_9_.stock_name IN ('极遨欧亚仓', '极遨美亚仓') THEN '极遨客户'
                    WHEN AKC_T_9_.stock_name = 'KST仓' THEN 'KST客户'
                    ELSE '调拨客户'
                END,
            '其他出库单')
        ) AS final_customer_type,
        CASE
            WHEN ARE_T_1_.passed is not null AND AST_T_2_.events_name = '销售出库' THEN '正常销售出库'
            WHEN ARE_T_1_.passed is not null AND AST_T_2_.events_name = '直接调拨' THEN '直接调拨'
            WHEN ARE_T_1_.passed is null AND AST_T_2_.events_name IN ('销售出库', '直接调拨', '其他出库') THEN '出库错误SN'
            WHEN ARE_T_1_.passed is not null AND AST_T_2_.events_name = '其他出库' THEN '其他出库'
            ELSE '其他SN'
        END AS flow_status,
        IF(AEC_T_11_.device_status = 7, '激活', '未激活') AS device_status_name,
        IF(AWE_T_7_.department_one_name is not null, AWE_T_7_.department_one_name, IF(AST_T_2_.events_name = '直接调拨', '直接调拨', '其他单据数据')) AS dept_l1,
        IF(AWE_T_7_.department_two_name is not null, AWE_T_7_.department_two_name, IF(AST_T_2_.events_name = '直接调拨', '直接调拨', '其他单据数据')) AS dept_l2,
        IF(AWE_T_7_.department_three_name is not null, AWE_T_7_.department_three_name, IF(AST_T_2_.events_name = '直接调拨', '直接调拨', '其他单据数据')) AS dept_l3,
        AST_T_2_.events_dep,
        AKC_T_9_.stock_name,
        AEC_T_11_.device_activated_country,
        AEC_T_11_.device_activated_province,
        AEC_T_11_.device_activated_city,
        AEC_T_11_.device_activated_district,
        AEC_T_11_.device_activated_address
    FROM `big_data_dw`.`dw_c_base_product_header` AS ARE_T_1_
    LEFT JOIN `big_data_dw`.`dw_c_base_product_events` AS AST_T_2_ ON ARE_T_1_.SN = AST_T_2_.SN
    LEFT JOIN `big_data_dw`.`dw_c_base_material` AS ALA_T_3_ ON AST_T_2_.material_id_1 = ALA_T_3_.material_id
    LEFT JOIN `big_data_dw`.`dw_c_base_auxiliary_information` AS ANO_T_4_ ON ALA_T_3_.material_spu = ANO_T_4_.id
    LEFT JOIN (
        SELECT '销售出库无仓库' as stock, outstock_dept_id as dep_id, outstock_man_id as sal_man, outstock_number as FBillNo, outstock_customer_id as cus_id, stock_link_country as contry FROM dw_c_sal_outstock
        UNION ALL
        SELECT r2.transfer_direct_detail_in_stock, '调拨无部门', '调拨无销售', r1.transfer_direct_bill_number, '调拨无客户', '-' FROM dw_c_sal_transfer_direct r1 LEFT JOIN dw_c_sal_transfer_direct_detail r2 ON r1.transfer_direct_id = r2.transfer_direct_id
        UNION ALL
        SELECT '其他出库无仓库', dept_id, '领料人', number, '其他出库无客户', '-' FROM dw_c_base_other_outstock
    ) AS A98_T_5_ ON SUBSTRING_INDEX(AST_T_2_.ID, '单', -1) = A98_T_5_.FBillNo
    LEFT JOIN `big_data_dw`.`dw_c_base_department` AS ATN_T_6_ ON A98_T_5_.dep_id = ATN_T_6_.department_id
    LEFT JOIN `big_data_dw`.`dw_c_base_department_relation_new` AS AWE_T_7_ ON ATN_T_6_.department_relation_id_new = AWE_T_7_.id
    LEFT JOIN `big_data_dw`.`dw_c_base_saleinfo` AS AOF_T_8_ ON A98_T_5_.sal_man = AOF_T_8_.sale_id
    LEFT JOIN `big_data_dw`.`dw_c_base_stock` AS AKC_T_9_ ON A98_T_5_.stock = AKC_T_9_.stock_id
    LEFT JOIN `big_data_dw`.`dw_c_base_customer` AS ARE_T_10_ ON A98_T_5_.cus_id = ARE_T_10_.customer_id
    LEFT JOIN `big_data_dw`.`dw_a_device` AS AEC_T_11_ ON ARE_T_1_.SN = AEC_T_11_.device_sn
    WHERE (AST_T_2_.events_name != '直接调拨' OR AKC_T_9_.stock_name IN (
            'Lazada迈金-马来西亚海外仓', 'Lazada迈金-新加坡海外仓', 'Lazada迈金-泰国海外仓',
            '东南亚三方仓-马来西亚海外仓', '东南亚三方仓-菲律宾海外仓', '速卖通-迈金-欧洲仓',
            'AE菜鸟深圳1号优选保税仓', '东莞菜鸟仓', 'Amazon-极遨-日本仓', '速卖通极遨-西班牙海外仓',
            '速卖通迈金-菜鸟美国仓', 'shopee-magene-新加坡官方仓', 'Shopee-GEOID-泰国南宁仓',
            '东南亚三方仓（元仓）-泰国海外仓', '乐金顺退货库', 'Shopee-GEOID-马来西亚海外仓',
            'Shopee-GEOID-泰国海外仓', 'Shopee-GEOID-菲律宾海外仓', 'Lazada-Magene-新加坡官方海外仓',
            '速卖通极遨-俄罗斯海外仓', '极遨-瑞豹仓', '速卖通极遨-烟台优选仓', '微盟一件代发库',
            'shopee-magene-优选仓', 'GEOID-Shopee-优选仓', '速卖通极遨-法国海外仓', '迈金独立站-法国谷仓',
            '迈金独立站-美国谷仓', '速卖通极遨-德国海外仓', '闪购门店仓-佰客屋廊坊', '闪购门店仓-佰客屋深圳',
            '闪购门店仓-佰客屋武汉', '闪购门店仓-佰客屋意风区', '闪购门店仓-佰客屋杭州', '闪购门店仓-佰客屋成都',
            '闪购门店仓-佰客屋武清', '闪购门店仓-佰客屋上海', '速卖通极遨海托法国仓', '速卖通极遨-波兰海外仓',
            '速卖通极遨海托波兰仓', '速卖通直营仓', '速卖通优选仓', '速卖通保税仓', '速卖通极遨-优选仓',
            '速卖通极遨-保税仓', '速卖通海外仓', '速卖通迈金-俄向乌兹仓', '速卖通迈金-烟台优选仓',
            '速卖通迈金巴西仓', '速卖通顽鹿-优选仓', '亚马逊仓', '日本亚马逊仓', '日本亚马逊仓（免税）',
            '春兰定制亚马逊库备货库', '欧洲亚马逊仓', '欧洲亚马逊仓库（免税）', '法国亚马逊仓', '澳洲亚马逊仓',
            '澳洲亚马逊仓（免税）', '独立站-乐金顺亚马逊仓', '美国亚马逊仓', 'Lazada极遨-中心仓',
            'Lazada迈金-中心仓', 'Lazada迈金-菲律宾海外仓', 'shopee-magene-泰国南宁仓',
            'shopee-magene-菲律宾海外仓', 'shopee-magene-马来西亚海外仓', '大森林美国海外仓',
            '极遨欧亚仓', '极遨美亚仓', 'KST仓'
      ) OR AST_T_2_.events_name != '直接调拨')
      AND ARE_T_1_.SN NOT LIKE 'FBA%' AND ARE_T_1_.SN NOT LIKE 'FBL%' AND ARE_T_1_.SN NOT LIKE 'FBS%'
      AND ARE_T_1_.SN NOT LIKE 'jstbx%' AND ARE_T_1_.SN NOT LIKE '优选仓%' AND ARE_T_1_.SN NOT LIKE 'XND%'
      AND ARE_T_1_.SN NOT LIKE '官方仓%' AND ARE_T_1_.SN NOT LIKE '云仓发%' AND ARE_T_1_.SN NOT LIKE '转FB%'
      AND ARE_T_1_.SN NOT LIKE '速卖通%' AND ARE_T_1_.SN NOT LIKE 'XNS%' AND ARE_T_1_.SN NOT LIKE 'XNP%'
      AND ARE_T_1_.SN NOT LIKE 'XNC%' AND ARE_T_1_.SN NOT LIKE 'SMT%' AND ARE_T_1_.SN NOT LIKE 'YMX%'
      AND ARE_T_1_.SN NOT LIKE '海外仓%' AND ARE_T_1_.SN NOT LIKE 'jst%' AND ARE_T_1_.SN NOT LIKE 'XNSN%'
      AND ARE_T_1_.SN NOT LIKE 'T%'
)
SELECT
    product_name AS spu_code,
    contry AS region,
    DATE_FORMAT(IF(device_status_name = '激活', active_at, events_date), '%%Y-%%m-%%d') AS business_date,
    COUNT(DISTINCT SN) AS activation_qty
FROM base_data
WHERE device_status_name = '激活'
  AND product_name = :spu_code
GROUP BY product_name, contry, DATE_FORMAT(IF(device_status_name = '激活', active_at, events_date), '%%Y-%%m-%%d')
"""


# 渠道取销售出库单关联的二级部门；出库业务日期取单据日期，激活取终端激活日期。
# 覆盖数仓全部可用历史（不再限定 2026 起），保证工作台任意周期都是同一真实出库/激活口径。
CHANNEL_ACTUALS_SYNC_SQL = """
WITH channel_base AS (
    SELECT DISTINCT
        h.SN,
        e.ID AS event_id,
        a.name AS spu_code,
        DATE(o.outstock_date) AS outbound_date,
        DATE(h.active_at) AS activation_date,
        h.passed,
        dev.device_status,
        CASE COALESCE(NULLIF(rel.department_two_name, ''), '未归属渠道')
            WHEN '国内渠道销售部' THEN '国内渠道'
            WHEN '国内电商销售部' THEN '国内电商'
            WHEN '海外渠道销售一部' THEN '国际渠道销售一部'
            WHEN '海外渠道销售二部' THEN '国际渠道销售二部'
            WHEN '海外电商销售部' THEN '海外电商'
            WHEN '跨境大客户部' THEN '跨境'
            ELSE COALESCE(NULLIF(rel.department_two_name, ''), '未归属渠道')
        END AS channel
    FROM big_data_dw.dw_c_base_product_header AS h
    JOIN big_data_dw.dw_c_base_product_events AS e
        ON h.SN = e.SN AND e.events_name = '销售出库'
    JOIN big_data_dw.dw_c_base_material AS m
        ON e.material_id_1 = m.material_id
    JOIN big_data_dw.dw_c_base_auxiliary_information AS a
        ON m.material_spu = a.id
    LEFT JOIN big_data_dw.dw_c_sal_outstock AS o
        ON SUBSTRING_INDEX(e.ID, '单', -1) = o.outstock_number
    LEFT JOIN big_data_dw.dw_c_base_department AS d
        ON o.outstock_dept_id = d.department_id
    LEFT JOIN big_data_dw.dw_c_base_department_relation_new AS rel
        ON d.department_relation_id_new = rel.id
    LEFT JOIN big_data_dw.dw_a_device AS dev
        ON h.SN = dev.device_sn
    WHERE a.name IN (
          SELECT DISTINCT spu
          FROM dwd_sales_forecast_import
          WHERE spu IS NOT NULL AND spu != ''
      )
      AND h.SN NOT LIKE 'FBA%' AND h.SN NOT LIKE 'FBL%' AND h.SN NOT LIKE 'FBS%'
      AND h.SN NOT LIKE 'jstbx%' AND h.SN NOT LIKE '优选仓%' AND h.SN NOT LIKE 'XND%'
      AND h.SN NOT LIKE '官方仓%' AND h.SN NOT LIKE '云仓发%' AND h.SN NOT LIKE '转FB%'
      AND h.SN NOT LIKE '速卖通%' AND h.SN NOT LIKE 'XNS%' AND h.SN NOT LIKE 'XNP%'
      AND h.SN NOT LIKE 'XNC%' AND h.SN NOT LIKE 'SMT%' AND h.SN NOT LIKE 'YMX%'
      AND h.SN NOT LIKE '海外仓%' AND h.SN NOT LIKE 'jst%' AND h.SN NOT LIKE 'XNSN%'
      AND h.SN NOT LIKE 'T%'
),
activation_base AS (
    SELECT
        channel_base.*,
        ROW_NUMBER() OVER (
            PARTITION BY SN
            ORDER BY
                (outbound_date <= activation_date) DESC,
                CASE WHEN outbound_date <= activation_date THEN outbound_date END DESC,
                CASE WHEN outbound_date > activation_date THEN outbound_date END ASC,
                event_id DESC
        ) AS activation_rank
    FROM channel_base
    WHERE device_status = 7
      AND passed IS NOT NULL
)
SELECT
    'outbound' AS metric,
    spu_code,
    outbound_date AS business_date,
    channel,
    COUNT(DISTINCT SN) AS quantity
FROM channel_base
WHERE passed IS NOT NULL AND outbound_date IS NOT NULL
GROUP BY spu_code, outbound_date, channel
UNION ALL
SELECT
    'activation' AS metric,
    spu_code,
    activation_date AS business_date,
    channel,
    COUNT(DISTINCT SN) AS quantity
FROM activation_base
WHERE activation_rank = 1
GROUP BY spu_code, activation_date, channel
ORDER BY spu_code, business_date, channel, metric
"""


# 2. 历史销售与出库标准查询 SQL (来自 sop数据清单.xlsx 第 2 项: 良发提供的 dw_a_sal_order_* 表)
HISTORICAL_SALES_SQL = """
SELECT
    mapping.spu_code,
    DATE(sales.FDate) AS business_date,
    SUM(sales.FQty) AS outbound_qty
FROM dw_c_sal_predict_jst_order AS sales
JOIN (
    SELECT
        product_code,
        MIN(forecast_model_spu) AS spu_code
    FROM import_sales_forecast_spu_model
    WHERE product_code IS NOT NULL AND product_code != ''
    GROUP BY product_code
    HAVING COUNT(DISTINCT forecast_model_spu) = 1
) AS mapping ON sales.Material_number = mapping.product_code
WHERE mapping.spu_code = :spu_code
  AND sales.Status IN ('Sent', 'Delivering')
  AND sales.FDate >= :start_date
  AND sales.FDate < DATE_ADD(:end_date, INTERVAL 1 DAY)
GROUP BY mapping.spu_code, DATE(sales.FDate)
ORDER BY business_date ASC
"""


# 3. 销售预测与提报标准查询 SQL (来自 sop数据清单.xlsx 第 3 项: dw_sal_predict_accuracy)
FORECAST_MONTHLY_SQL = """
SELECT
    spu_code,
    region,
    channel,
    forecast_month,
    forecast_type,
    SUM(forecast_qty) AS forecast_qty,
    version
FROM dw_sal_predict_accuracy
WHERE spu_code = :spu_code
  AND forecast_month >= :start_month
GROUP BY spu_code, region, channel, forecast_month, forecast_type, version
ORDER BY forecast_month ASC
"""


# 4. SPU 映射标准查询 SQL (来自 sop数据清单.xlsx 第 6 项: import_sales_forecast_spu_model)
SPU_MAPPING_SQL = """
SELECT
    canonical_spu_code AS spu_code,
    spu_name,
    product_line,
    brand,
    category,
    lifecycle_stage,
    source_spu_code,
    confidence
FROM import_sales_forecast_spu_model
WHERE is_active = 1
"""


# 5. 库存与在途标准查询 SQL (来自 sop数据清单.xlsx 第 4 项: dws_spu_material_stock_detail_semi)
INVENTORY_STOCK_SQL = """
SELECT
    spu_code,
    warehouse_name,
    region,
    available_stock_qty,
    in_transit_qty,
    safe_stock_days,
    inventory_coverage_weeks,
    as_of_date
FROM dws_spu_material_stock_detail_semi
WHERE spu_code = :spu_code
ORDER BY as_of_date DESC
LIMIT 100
"""
