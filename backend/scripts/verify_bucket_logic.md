#!/bin/bash
# 剩余期限桶计算逻辑 —— 代码 vs 业务描述 逐步核对
echo "=============================================================="
echo " 核对 1：每月投放落在哪些格（规则 M+v）"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT r.date_offset AS 投放月,
       ROUND(r.month_add/1e8,4) AS add_纯新增,
       ROUND((r.month_release + r.month_add)/1e8,4) AS month_new_投放总额,
       1+12 AS 期限12落点, 1+24 AS 期限24落点, 1+36 AS 期限36落点, 1+60 AS 期限60落点
FROM prcp_sim_result r
WHERE r.run_id=20 AND r.node_code='S010101010000' AND r.date_offset IN (1,2,3)
ORDER BY r.date_offset;
" 2>&1 | grep -v Warning

echo ""
echo "=============================================================="
echo " 核对 2：M13 到期 = M1 的 12 月期部分"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT ROUND(month_release/1e8,4) AS M13到期额,
       ROUND(month_release/0.2/1e8,4) AS 反推M1投放总额,
       (SELECT ROUND((month_release+month_add)/1e8,4) FROM prcp_sim_result
         WHERE run_id=20 AND node_code='S010101010000' AND date_offset=1) AS M1实际投放总额
FROM prcp_sim_result
WHERE run_id=20 AND node_code='S010101010000' AND date_offset=13;
" 2>&1 | grep -v Warning

echo ""
echo "=============================================================="
echo " 核对 3：M25 到期 = M1的24月期 + M13的12月期 + 存量"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT ROUND(month_release/1e8,4) AS M25到期额
FROM prcp_sim_result WHERE run_id=20 AND node_code='S010101010000' AND date_offset=25;
SELECT 'M1投放x30%(24月期)' AS 来源,
  ROUND((SELECT month_release+month_add FROM prcp_sim_result
    WHERE run_id=20 AND node_code='S010101010000' AND date_offset=1)*0.30/1e8,4) AS 金额;
SELECT 'M13投放x20%(12月期)' AS 来源,
  ROUND((SELECT month_release+month_add FROM prcp_sim_result
    WHERE run_id=20 AND node_code='S010101010000' AND date_offset=13)*0.20/1e8,4) AS 金额;
" 2>&1 | grep -v Warning

echo ""
echo "=============================================================="
echo " 核对 4：完整排期 full_plan 累加守恒"
echo "  (full_plan 应= 存量 + Σ60个月投放)"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT
 (SELECT ROUND(SUM(month_release),2)/1e8 FROM prcp_sim_result
   WHERE run_id=20 AND node_code='S010101010000' AND is_aggregated=0) AS 实际60月释放,
 (SELECT ROUND(SUM(month_add+month_release),2)/1e8 FROM prcp_sim_result
   WHERE run_id=20 AND node_code='S010101010000' AND is_aggregated=0) AS Σ投放到期(超60月部分在y10),
 (SELECT ROUND(cum_planned,2)/1e8 FROM prcp_sim_result
   WHERE run_id=20 AND node_code='S010101010000' AND date_offset=60) AS 累计投放,
 (SELECT ROUND(current_balance/1e8,2) FROM prcp_data_basic
   WHERE data_date='2025-12-31' AND is_deleted=0 AND node_code='S010101010000') AS 基准日余额;
" 2>&1 | grep -v Warning

echo ""
echo "=============================================================="
echo " 核对 5：每年末余额 = 上年末 + 当年净增（目标类回补口径）"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT FLOOR((date_offset-1)/12)+1 AS 年度,
       ROUND(SUM(month_add)/1e8,2) AS Σ分摊新增,
       ROUND(SUM(month_release)/1e8,2) AS Σ到期释放,
       ROUND(SUM(month_add)/1e8 - SUM(month_release)/1e8,2) AS 净增_Σadd-Σrel,
       ROUND(MAX(CASE WHEN MOD(date_offset,12)=0 THEN current_balance END)/1e8,2) AS 年末余额
FROM prcp_sim_result WHERE run_id=20 AND node_code='S010101010000'
GROUP BY FLOOR((date_offset-1)/12)+1 ORDER BY 年度;
" 2>&1 | grep -v Warning

echo ""
echo "=============================================================="
echo " 核对 6：余额恒等式 new_cb = base_cb + add"
echo "=============================================================="
mysql -u prcp -pPrcp@2026 prcp_db -e "
SELECT ROUND(SUM(CASE WHEN month_add+month_release<>0
  THEN 1 ELSE 0 END),0) AS 记录数,
  ROUND(MAX(ABS(current_balance - LAG(current_balance) OVER (ORDER BY date_offset) - month_add)),6) AS 最大偏差_元
FROM prcp_sim_result WHERE run_id=20 AND node_code='S010101010000';
" 2>&1 | grep -v Warning