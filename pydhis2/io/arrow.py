"""Arrow format converter"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path


class ArrowConverter:
    """Arrow format converter"""
    
    def __init__(self):
        self.compression = 'snappy'  # Default compression format
    
    def from_pandas(self, df: pd.DataFrame, schema: Optional[pa.Schema] = None) -> pa.Table:
        """Convert from Pandas DataFrame to Arrow Table"""
        if df.empty:
            return pa.table({})
        
        try:
            if schema is not None:
                table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
            else:
                table = pa.Table.from_pandas(df, preserve_index=False)
            return table
        except Exception as e:
            # Fallback to basic conversion
            return pa.Table.from_pandas(df, preserve_index=False)
    
    def to_pandas(self, table: pa.Table) -> pd.DataFrame:
        """Convert from Arrow Table to Pandas DataFrame"""
        return table.to_pandas()
    
    def save_parquet(
        self,
        table: pa.Table,
        file_path: Union[str, Path],
        compression: str = None,
        partition_cols: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Save as Parquet file"""
        file_path = Path(file_path)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        compression = compression or self.compression
        
        if partition_cols:
            # Partitioned write
            pq.write_to_dataset(
                table,
                root_path=str(file_path.parent),
                partition_cols=partition_cols,
                compression=compression,
                **kwargs
            )
        else:
            # Single file write
            pq.write_table(
                table,
                str(file_path),
                compression=compression,
                **kwargs
            )
        
        return str(file_path)
    
    def load_parquet(self, file_path: Union[str, Path]) -> pa.Table:
        """Load from Parquet file"""
        return pq.read_table(str(file_path))
    
    def save_feather(self, table: pa.Table, file_path: Union[str, Path]) -> str:
        """Save as Feather file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to pandas then save (Feather v2 format)
        df = self.to_pandas(table)
        df.to_feather(str(file_path))
        
        return str(file_path)
    
    def load_feather(self, file_path: Union[str, Path]) -> pa.Table:
        """Load from Feather file"""
        df = pd.read_feather(str(file_path))
        return self.from_pandas(df)
    
    def get_schema_info(self, table: pa.Table) -> Dict[str, Any]:
        """Get Schema information"""
        schema = table.schema
        
        info = {
            'num_columns': len(schema),
            'num_rows': len(table),
            'columns': []
        }
        
        for field in schema:
            column_info = {
                'name': field.name,
                'type': str(field.type),
                'nullable': field.nullable,
                'metadata': dict(field.metadata) if field.metadata else {}
            }
            info['columns'].append(column_info)
        
        return info
    
    def optimize_schema(self, df: pd.DataFrame) -> pa.Schema:
        """Optimize Schema to reduce storage space"""
        fields = []
        
        for column in df.columns:
            dtype = df[column].dtype
            field_type = None
            
            if pd.api.types.is_integer_dtype(dtype):
                # Choose the smallest integer type
                min_val = df[column].min()
                max_val = df[column].max()
                
                if pd.isna(min_val) or pd.isna(max_val):
                    field_type = pa.int64()
                elif min_val >= 0:
                    # Unsigned integer
                    if max_val <= 255:
                        field_type = pa.uint8()
                    elif max_val <= 65535:
                        field_type = pa.uint16()
                    elif max_val <= 4294967295:
                        field_type = pa.uint32()
                    else:
                        field_type = pa.uint64()
                else:
                    # Signed integer
                    if min_val >= -128 and max_val <= 127:
                        field_type = pa.int8()
                    elif min_val >= -32768 and max_val <= 32767:
                        field_type = pa.int16()
                    elif min_val >= -2147483648 and max_val <= 2147483647:
                        field_type = pa.int32()
                    else:
                        field_type = pa.int64()
            
            elif pd.api.types.is_float_dtype(dtype):
                # Check if float32 can be used
                if df[column].dtype == 'float64':
                    # Simple check: if all values are within float32 range
                    field_type = pa.float32()
                else:
                    field_type = pa.float64()
            
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                field_type = pa.timestamp('ns')
            
            elif pd.api.types.is_bool_dtype(dtype):
                field_type = pa.bool_()
            
            else:
                # String type - check if suitable for dictionary encoding
                unique_ratio = df[column].nunique() / len(df)
                if unique_ratio < 0.5:  # If unique value ratio is low, use dictionary encoding
                    field_type = pa.dictionary(pa.int32(), pa.string())
                else:
                    field_type = pa.string()
            
            # Check for missing values
            nullable = df[column].isna().any()
            
            fields.append(pa.field(column, field_type, nullable=nullable))
        
        return pa.schema(fields)
    
    def compress_table(self, table: pa.Table) -> pa.Table:
        """Compress table (dictionary encoding, etc.)"""
        columns = []
        
        for i in range(table.num_columns):
            column = table.column(i)
            column_name = table.schema.field(i).name
            
            # Apply dictionary encoding to string columns
            if pa.types.is_string(column.type):
                # Calculate unique value ratio
                unique_count = pa.compute.count_distinct(column).as_py()
                total_count = len(column)
                
                if unique_count / total_count < 0.5:  # Low unique value ratio
                    try:
                        # Apply dictionary encoding
                        encoded_column = pa.compute.dictionary_encode(column)
                        columns.append(encoded_column)
                        continue
                    except Exception:
                        pass
            
            columns.append(column)
        
        # Build new schema
        fields = []
        for i, column in enumerate(columns):
            field_name = table.schema.field(i).name
            fields.append(pa.field(field_name, column.type))
        
        new_schema = pa.schema(fields)
        
        return pa.table(columns, schema=new_schema)
    
    def estimate_size(self, table: pa.Table) -> Dict[str, Any]:
        """Estimate table size"""
        # Get memory usage
        memory_size = table.nbytes
        
        # Estimate compressed size (based on empirical values)
        estimated_parquet_size = memory_size * 0.2  # Parquet usually compresses to 20%
        estimated_feather_size = memory_size * 0.8   # Feather compresses to 80%
        
        return {
            'memory_bytes': memory_size,
            'memory_mb': memory_size / 1024 / 1024,
            'estimated_parquet_mb': estimated_parquet_size / 1024 / 1024,
            'estimated_feather_mb': estimated_feather_size / 1024 / 1024,
            'num_rows': len(table),
            'num_columns': table.num_columns,
        }
