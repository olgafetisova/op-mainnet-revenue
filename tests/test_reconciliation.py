from pathlib import Path

import duckdb
import pytest

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "opm.duckdb"
# growthepie fees_paid_eth for optimism is inflated on these days (2025-04-13 exactly doubled);
# its txcount and rent_paid_eth look normal and file 01 agrees with the neighbouring days.
GTP_FEE_ANOMALY_DAYS = ("2025-04-13", "2025-04-14")


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


def test_contract_activity_sums_to_daily_fees(con):
    # every ETH value is rounded to 1e-6, so a day's sum can drift by up to 1e-6 per row
    mismatches = con.sql("""
        select f.date, f.total_fee_eth, a.total_fee_eth, f.fee_paying_txs, a.txs
        from fees_daily f
        join (select date, sum(total_fee_eth) total_fee_eth, sum(txs) txs, count(*) n_rows
              from contract_activity group by 1) a using (date)
        where abs(f.total_fee_eth - a.total_fee_eth) > 1e-6 * a.n_rows or f.fee_paying_txs != a.txs
    """).fetchall()
    days = con.sql("select count(distinct date) from contract_activity").fetchone()[0]
    assert days == con.sql("select count(*) from fees_daily").fetchone()[0]
    assert mismatches == []


def test_growthepie_fees_match_daily_fees_monthly(con):
    rows = con.sql("""
        with g as (
            select date_trunc('month', date) as month, sum(value) gtp_eth
            from gtp_metrics where origin_key = 'optimism' and metric_key = 'fees_paid_eth'
              and date::varchar not in $anomaly_days
            group by 1
        ), f as (
            select date_trunc('month', date) as month, sum(total_fee_eth) fee_eth
            from fees_daily where date::varchar not in $anomaly_days
            group by 1
        )
        select month, gtp_eth, fee_eth from f join g using (month)
        where month between date '2025-01-01' and date '2026-08-01'
        order by month
    """, params={"anomaly_days": list(GTP_FEE_ANOMALY_DAYS)}).fetchall()
    assert len(rows) == 20
    off = [(m, g, f) for m, g, f in rows if abs(g - f) / f > 0.0015]  # worst full month observed: 0.099%
    assert off == []


def test_daily_fees_and_l1_cost_are_complete(con):
    # notebook 01's daily P&L: one row per file 01 day, growthepie L1 cost (rent_paid_eth) on almost every day
    days, missing_rent, negative_gross, no_price = con.sql("""
        select count(*), count(*) filter (where r.value is null), count(*) filter (where f.total_fee_eth < 0),
               count(*) filter (where f.eth_price_usd is null)
        from fees_daily f
        left join gtp_metrics r on r.date = f.date and r.origin_key = 'optimism' and r.metric_key = 'rent_paid_eth'
    """).fetchone()
    assert days == 623
    assert missing_rent <= 5, f"{missing_rent} days without growthepie rent_paid_eth"
    assert negative_gross == 0 and no_price == 0


def test_every_named_address_is_labelled(con):
    unlabelled = con.sql("""
        select distinct to_address from contract_activity
        where to_address != 'other' and to_address not in (select address from labels)
    """).fetchall()
    assert unlabelled == []


def test_customer_mapping(con):
    segments = {"dex", "lending", "stablecoin_payments", "bridge_messaging", "oracle_infra", "bots_automation", "cex", "nft_social",
                "other_labeled", "unlabeled", "long_tail"}
    # one row per file 07 address plus the 'other' row, each with an app and an allowed segment; one segment per app
    rows, addresses, apps = con.sql("select count(*), count(distinct address), count(app) from m_customer_app").fetchone()
    assert rows == addresses == apps == con.sql("select count(*) from labels").fetchone()[0] + 1
    used = {s for (s,) in con.sql("select distinct segment from m_customer_app union select distinct address_segment from m_customer_app").fetchall()}
    assert used <= segments
    assert con.sql("select app from m_customer_app group by app having count(distinct segment) > 1").fetchall() == []
    # unnamed apps never merge unrelated addresses; Wintermute = two labelled contracts + the inferred successor
    assert con.sql("""select app from m_customer_app where app like 'unlabeled-%' and source <> 'override'
                      group by app having count(*) > 1""").fetchall() == []
    assert con.sql("select count(*) from m_customer_app where app = 'wintermute'").fetchone()[0] == 3
    # overrides: known addresses, allowed segments, evidence written down
    bad = con.sql("""select o.address from address_overrides o left join labels l using (address)
                     where l.address is null or length(o.evidence) <= 80""").fetchall()
    assert bad == []
    assert {s for (s,) in con.sql("select distinct segment from address_overrides").fetchall()} <= segments
    # every top-40 TTM address without project, namespace or owner is curated
    uncurated = con.sql("""
        with t as (select to_address as address, sum(total_fee_usd) as fee_usd from contract_activity
                   where date between '2025-09-16' and '2026-09-15' and to_address <> 'other'
                   group by 1 order by fee_usd desc limit 40)
        select t.address from t join labels l using (address)
        where l.entity_project is null and l.dune_namespace is null and l.dune_owner is null
          and t.address not in (select address from address_overrides)
    """).fetchall()
    assert uncurated == []
    # monthly mart reconciles to file 01 within 0.1%
    month_usd, file01_usd = con.sql("select (select sum(fee_usd) from m_customer_month), (select sum(total_fee_usd) from fees_daily)").fetchone()
    assert abs(month_usd / file01_usd - 1) < 1e-3
