CREATE TABLE [c360].[dim_customer_360] (

	[customer_id] varchar(50) NULL, 
	[full_name] varchar(200) NULL, 
	[region] varchar(50) NULL, 
	[customer_segment] varchar(50) NULL, 
	[rm_id] varchar(50) NULL, 
	[total_transactions] int NULL, 
	[total_transaction_amount] decimal(18,2) NULL, 
	[kyc_status] varchar(50) NULL, 
	[risk_rating] varchar(50) NULL, 
	[email] varchar(200) NULL, 
	[document_number] varchar(100) NULL
);