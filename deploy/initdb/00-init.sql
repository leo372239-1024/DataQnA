-- DataQnA 初始化：创建扩展与只读分析角色
-- 由 docker-entrypoint-initdb.d 在首次启动时执行

CREATE EXTENSION IF NOT EXISTS vector;

-- 分析只读角色（应用以该角色执行分析查询，结构性防写）
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytics_ro') THEN
    CREATE ROLE analytics_ro LOGIN PASSWORD 'analytics_ro';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE dataqna TO analytics_ro;
