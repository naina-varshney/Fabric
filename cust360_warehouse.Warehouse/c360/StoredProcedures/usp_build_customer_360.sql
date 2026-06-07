CREATE PROCEDURE c360.usp_build_customer_360
    @as_of_date DATE
AS
BEGIN
    TRUNCATE TABLE c360.dim_customer_360;

    INSERT INTO c360.dim_customer_360
    SELECT 
        c.customer_id,
        c.full_name,
        c.region,
        c.customer_segment,
        c.rm_id,
        COUNT(CASE WHEN t.transaction_status = 'Success' THEN 1 END),
        SUM(CASE WHEN t.transaction_status = 'Success' THEN t.transaction_amount ELSE 0 END),
        k.kyc_status,
        k.risk_rating,
        c.email,
        k.document_number
    FROM cust360_lakehouse.dbo.bronze_crm_customers c
    LEFT JOIN cust360_lakehouse.dbo.bronze_transactions t
        ON c.customer_id = t.customer_id
    LEFT JOIN cust360_lakehouse.dbo.bronze_kyc_records k
        ON c.customer_id = k.customer_id
    GROUP BY 
        c.customer_id, c.full_name, c.region,
        c.customer_segment, c.rm_id,
        k.kyc_status, k.risk_rating,
        c.email, k.document_number;
END;