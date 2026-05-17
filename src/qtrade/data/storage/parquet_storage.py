import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Optional
from qtrade.core.errors import DataError
from qtrade.core.log import get_logger

logger = get_logger("parquet_storage")


class ParquetStorage:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema: Optional[pa.Schema] = None,
        partition_cols: Optional[list[str]] = None,
    ) -> None:
        if df.empty:
            logger.info("Empty DataFrame, skipping save.", table_name=table_name)
            return

        try:
            table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
            output_path = os.path.join(self.base_dir, table_name)

            pq.write_to_dataset(
                table,
                root_path=output_path,
                partition_cols=partition_cols,
                use_dictionary=True,
                compression="snappy",
            )
            logger.info(
                "Saved data successfully", table_name=table_name, path=output_path
            )
        except Exception as e:
            logger.error("Failed to save parquet", table_name=table_name, error=str(e))
            raise DataError(f"Failed to save parquet for {table_name}: {e}")

    def load(
        self,
        table_name: str,
        columns: Optional[list[str]] = None,
        filters: Optional[list[tuple]] = None,
    ) -> pd.DataFrame:
        input_path = os.path.join(self.base_dir, table_name)
        if not os.path.exists(input_path):
            logger.warning("Dataset not found", table_name=table_name, path=input_path)
            return pd.DataFrame()

        try:
            dataset = pq.ParquetDataset(input_path, filters=filters)
            table = dataset.read(columns=columns)
            return table.to_pandas()
        except Exception as e:
            logger.error("Failed to load parquet", table_name=table_name, error=str(e))
            raise DataError(f"Failed to load parquet for {table_name}: {e}")
