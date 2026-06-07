CREATE FUNCTION c360.fn_rls_region(@region VARCHAR(50))
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN
SELECT 1 AS access_flag
WHERE EXISTS (
    SELECT 1
    FROM c360.rm_region_map r
    WHERE r.rm_login = USER_NAME()
      AND r.region = @region
);