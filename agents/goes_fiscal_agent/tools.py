# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This file contains the tools used by the database agent."""

from google.api_core import exceptions

from .utils import get_env_var

from google.cloud import bigquery
from google.genai import Client


project_id = get_env_var("BQ_PROJECT_ID")
dataset_id = get_env_var("BQ_DATASET_ID")

llm_client = Client(vertexai=True, project=project_id)

bq_client = bigquery.Client(project=project_id)

def get_bigquery_schema():
    """Retrieves schema and generates DDL with example values for a BigQuery dataset.

    Args:
        dataset_id (str): The ID of the BigQuery dataset (e.g., 'my_dataset').
        client (bigquery.Client): A BigQuery client.
        project_id (str): The ID of your Google Cloud Project.

    Returns:
        str: A string containing the generated DDL statements.
    """

    # dataset_ref = client.dataset(dataset_id)
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)

    ddl_statements = ""

    for table in bq_client.list_tables(dataset_ref):
        table_ref = dataset_ref.table(table.table_id)
        table_obj = bq_client.get_table(table_ref)

        # Check if table is a view
        if table_obj.table_type != "TABLE":
            continue

        ddl_statement = f"CREATE OR REPLACE TABLE `{table_ref}` (\n"

        for field in table_obj.schema:
            ddl_statement += f"  `{field.name}` {field.field_type}"
            if field.mode == "REPEATED":
                ddl_statement += " ARRAY"
            if field.description:
                ddl_statement += f" COMMENT '{field.description}'"
            ddl_statement += ",\n"

        ddl_statement = ddl_statement[:-2] + "\n);\n\n"

        # Add example values if available (limited to first row)
        rows = bq_client.list_rows(table_ref, max_results=5).to_dataframe()
        if not rows.empty:
            ddl_statement += f"-- Example values for table `{table_ref}`:\n"
            for _, row in rows.iterrows():  # Iterate over DataFrame rows
                ddl_statement += f"INSERT INTO `{table_ref}` VALUES\n"
                example_row_str = "("
                for value in row.values:  # Now row is a pandas Series and has values
                    if isinstance(value, str):
                        example_row_str += f"'{value}',"
                    elif value is None:
                        example_row_str += "NULL,"
                    else:
                        example_row_str += f"{value},"
                example_row_str = (
                    example_row_str[:-1] + ");\n\n"
                )  # remove trailing comma
                ddl_statement += example_row_str

        ddl_statements += ddl_statement

    return ddl_statements

def run_bigquery_query(sql_query: str) -> str:
    """
    Executa uma consulta SQL no Google BigQuery e retorna o resultado como uma string JSON.

    Esta função é a "ferramenta" que o agente LLM chamará para obter dados.
    É crucial que o retorno seja um formato que o LLM possa interpretar facilmente, como JSON.

    Args:
        sql_query (str): A consulta SQL a ser executada no BigQuery.

    Returns:
        str: Uma string contendo os resultados da consulta em formato JSON,
             ou uma mensagem de erro se a consulta falhar.
    """
    if not bq_client:
        return "Erro: O cliente BigQuery não está inicializado. Verifique a autenticação."

    print(f"\n[Tool Executing] Executando a seguinte consulta:\n--- --- ---\n{sql_query}\n--- --- ---")

    try:
        # Executa a consulta
        query_job = bq_client.query(sql_query)

        # Espera o resultado e converte para um DataFrame do Pandas
        results_df = query_job.to_dataframe()

        if results_df.empty:
            print("[Tool Result] A consulta não retornou resultados.")
            return "A consulta foi executada com sucesso, mas não encontrou dados."

        # Converte o DataFrame para uma string JSON
        # O formato 'records' cria uma lista de dicionários, ideal para LLMs
        json_result = results_df.to_json(orient="records", indent=2, date_format='iso')

        print(f"[Tool Result] Retornando {len(results_df)} registros.")
        return json_result

    except exceptions.GoogleAPICallError as e:
        # Captura erros específicos da API do Google (ex: SQL inválido, permissões)
        error_message = f"Erro na API do BigQuery: {e.message}"
        print(f"[Tool Error] {error_message}")
        return error_message
    except Exception as e:
        # Captura outros erros inesperados
        error_message = f"Ocorreu um erro inesperado ao executar a consulta: {str(e)}"
        print(f"[Tool Error] {error_message}")
        return error_message