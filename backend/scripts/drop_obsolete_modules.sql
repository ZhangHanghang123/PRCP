-- 删除已下架模块的数据库表（资金组/头寸/组算规则/组算任务）
-- 注意：本操作不可逆，删除前已备份 prcp_db_backup_20260909.sql
DROP TABLE IF EXISTS prcp_task_log;
DROP TABLE IF EXISTS prcp_task;
DROP TABLE IF EXISTS prcp_position;
DROP TABLE IF EXISTS prcp_rule;
DROP TABLE IF EXISTS prcp_group;