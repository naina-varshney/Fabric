# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "3cf24b0d-234e-439b-9090-b10204ecd5fc",
# META       "default_lakehouse_name": "cust360_lakehouse",
# META       "default_lakehouse_workspace_id": "7b173a49-4de9-4c8d-b703-1584ec15bdc0",
# META       "known_lakehouses": [
# META         {
# META           "id": "3cf24b0d-234e-439b-9090-b10204ecd5fc"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


def load_bronze(file_name, table_name, source_system):
    
    df = spark.read.format("csv") \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .load(f"Files/{file_name}")
    
    df = df.withColumn("source_system", lit(source_system)) \
           .withColumn("source_file_name", lit(file_name)) \
           .withColumn("ingestion_timestamp", current_timestamp()) \
           .withColumn("pipeline_run_id", lit("run_001"))
    
    df.write.format("delta") \
        .mode("overwrite") \
        .saveAsTable(table_name)
    
    print(f"{table_name} loaded successfully ✅")





# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 1. CRM Customers
# load_bronze(
#     "crm_customers.csv",
#     "bronze_crm_customers",
#     "CRM"
# )

# 2. CRM Interactions
load_bronze(
    "crm_interactions.csv",
    "bronze_crm_interactions",
    "CRM"
)

# 3. Transactions
load_bronze(
    "transactions.csv",
    "bronze_transactions",
    "Transactions"
)

# 4. KYC Records
load_bronze(
    "kyc_records.csv",
    "bronze_kyc_records",
    "KYC"
)

# 5. Relationship Managers
load_bronze(
    "relationship_managers.csv",
    "bronze_relationship_managers",
    "Reference"
)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
