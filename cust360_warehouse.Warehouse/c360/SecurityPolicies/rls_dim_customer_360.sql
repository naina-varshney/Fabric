CREATE SECURITY POLICY c360.rls_dim_customer_360
ADD FILTER PREDICATE c360.fn_rls_region([region])
    ON [c360].[dim_customer_360]
WITH (STATE = ON);
