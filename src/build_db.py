from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CASE_CSV = ROOT / "case_study_data" / "csv"
EXTERNAL = ROOT / "data" / "external"
CASE_TABLES = {
    "fees_daily": "01_opm_fees_daily.csv",
    "eth_price": "02_eth_price_daily.csv",
    "activity": "03_opm_activity_daily.csv",
    "new_addresses": "04_opm_new_addresses_daily.csv",
    "deployments": "05_opm_contract_deployments_daily.csv",
    "contract_activity": "06_opm_contract_activity_daily.csv",
    "labels": "07_opm_contract_labels.csv",
    "app_fees": "08_opm_app_fees_revenue_daily.csv",
    "dex_volume": "09_opm_dex_volume_daily.csv",
    "lending": "10_opm_lending_daily.csv",
    "tvl": "11_opm_tvl_by_protocol_daily.csv",
    "stablecoins": "12_opm_stablecoins_daily.csv",
    "bridge_flows": "13_opm_bridge_flows_daily.csv",
    "cex_flows": "14_opm_cex_flows_daily.csv",
}
EXTERNAL_TABLES = {
    "gtp_metrics": "growthepie_metrics.csv",
    "op_block_headers": "op_block_headers.csv",
}


def load_csv(con: duckdb.DuckDBPyConnection, table: str, path: Path) -> None:
    with path.open() as f:
        has_date = "date" in f.readline().strip().split(",")
    types = ", types = {'date': 'DATE'}" if has_date else ""
    con.execute(f"create table {table} as select * from read_csv_auto('{path}'{types})")


def build(db_path: str = "data/opm.duckdb") -> None:
    db = ROOT / db_path
    db.unlink(missing_ok=True)
    with duckdb.connect(str(db)) as con:
        for table, name in CASE_TABLES.items():
            load_csv(con, table, CASE_CSV / name)
        for table, name in EXTERNAL_TABLES.items():
            load_csv(con, table, EXTERNAL / name)
        con.execute(f"set file_search_path = '{ROOT}'")  # relative paths in sql/*.sql resolve from the repo root
        for sql in sorted((ROOT / "sql").glob("*.sql")):
            con.execute(sql.read_text())


if __name__ == "__main__":
    build()
