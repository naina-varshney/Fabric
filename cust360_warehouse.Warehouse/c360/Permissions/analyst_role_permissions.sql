GRANT SELECT ON OBJECT::[c360].[dim_customer_360] TO [analyst_role];

DENY SELECT ON [c360].[dim_customer_360]([email]) TO [analyst_role];

DENY SELECT ON [c360].[dim_customer_360]([document_number]) TO [analyst_role];

DENY SELECT ON OBJECT::[c360].[rm_region_map] TO [analyst_role];
