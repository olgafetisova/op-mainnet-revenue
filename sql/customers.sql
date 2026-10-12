-- Customers = apps that receive the transactions paying OP Mainnet sequencer fees (file 06, by to_address).
-- Shared by all three notebooks and the tests. TTM = 2025-09-16 .. 2026-09-15.

-- Name normalisation shared by labels (file 07) and DefiLlama protocols (file 08):
-- lowercase, drop dots, non-alphanumerics -> '-', strip version suffixes (-v2, _v3, v1_5, -v5-beta)
-- and corporate suffixes (-finance, -protocol, ...), then map known aliases of the same brand.
create or replace macro slug_base(x) as regexp_replace(regexp_replace(regexp_replace(regexp_replace(
    replace(lower(trim(x)), '.', ''), '[^a-z0-9]+', '-', 'g'), '^-+|-+$', '', 'g'),
    '-v[0-9]+(-[0-9]+)?(-beta)?$', ''), '-(finance|protocol|network|xyz|exchange|foundation)$', '');

create or replace macro app_slug(x) as case slug_base(x)
    when 'sushi' then 'sushiswap'
    when 'layer-zero' then 'layerzero'
    when 'oneinch' then '1inch'
    when 'kyber' then 'kyberswap'
    when 'zeroex' then '0x'
    when '0x-api' then '0x'
    when 'okx-dex' then 'okx'
    when '0xsquid' then 'squid'
    when 'squid-router' then 'squid'
    when 'odos-v3-router' then 'odos'
    when 'mayan-swift' then 'mayan'
    when 'perp' then 'perpetual'
    when 'woonetwork' then 'woofi'
    when 'farcasterxyz' then 'farcaster'
    when 'gasdotzip' then 'gaszip'
    when 'ewya' then 'eywa'
    when 'paraswap' then 'velora'                 -- ParaSwap rebranded to Velora
    when 'holonym' then 'human'                   -- Holonym = Human ID / Human Passport (DefiLlama human-protocol)
    when 'seaport' then 'opensea'
    when 'rainbow-swap-aggregator' then 'rainbow'
    when 'synthetix-futuresmarket' then 'synthetix'
    when 'gnosis-safe' then 'safe'
    when 'safe-global' then 'safe'
    when 'alchemyplatform' then 'erc4337'         -- canonical EntryPoint v0.7, credited to Alchemy by Allium
    when 'eth-infinitism-account-abstraction' then 'erc4337'
    when 'optimism-usdc' then 'circle'
    when 'usdt' then 'tether'
    when 'op' then 'optimism'
    when 'optimism-governor' then 'optimism'
    else slug_base(x) end;

create or replace table address_overrides as
select * from read_csv('data/overrides/address_overrides.csv', header = true, all_varchar = true);

-- Address -> app. Overrides first, then labels: entity_project > dune_namespace > dune_owner > display_name.
-- dune_namespace: first value that is not gnosis_safe (Safe is a wallet shell, not the app).
-- dune_owner: 'sushiswap' is ignored; Dune assigns it to Multicall3, LayerZero, Squid, Safe wallets and bots.
-- display_name: only 'Brand: Contract' names; bare contract names (StrategyExecutor, Trading Bot, Router) are not brands.
-- Unnamed addresses are keyed by their full address ('unlabeled-<40 hex>') so prefix-sharing contracts never merge;
-- curated overrides keep their short 'unlabeled-<6 hex>' slugs, which group same-deployer contracts on purpose.
create or replace table m_customer_app as
with bot as (  -- bot rule: some month with peak daily distinct senders <= 10 and >= 100k txs
    select distinct to_address as address from (
        select to_address, date_trunc('month', date) as month, sum(txs) as txs, max(distinct_senders) as peak_senders
        from contract_activity where to_address <> 'other' group by 1, 2)
    where peak_senders <= 10 and txs >= 100000
),
fees as (
    select to_address as address, sum(total_fee_usd) filter (where date between '2025-09-16' and '2026-09-15') as ttm_fee_usd,
           sum(total_fee_usd) as all_fee_usd
    from contract_activity group by 1
),
l as (
    select l.*,
        coalesce(list_filter(string_split(dune_namespace, ' | '), x -> x <> 'gnosis_safe')[1],
                 string_split(dune_namespace, ' | ')[1]) as namespace,
        list_filter(string_split(dune_owner, ' | '), x -> x <> 'sushiswap')[1] as owner,
        case when display_name like '%: %' and display_name not like 'Null Address%'
             then split_part(display_name, ': ', 1) end as display_brand
    from labels l
),
named as (
    select l.*,
        coalesce(app_slug(entity_project), app_slug(namespace), app_slug(owner), app_slug(display_brand)) as label_app,
        case when entity_project is not null then 'entity_project' when namespace is not null then 'dune_namespace'
             when owner is not null then 'dune_owner' when display_brand is not null then 'display_name'
             else 'unlabeled' end as label_source
    from l
),
seg as (
    select n.*,
        case
            when dune_cex_name is not null or entity_category = 'cex' or tags like '%cex%' then 'cex'
            when entity_category in ('mev', 'trading', 'market_maker') then 'bots_automation'
            when entity_category in ('stablecoin', 'payments') or label_app in ('tether', 'circle')
                 or upper(dune_token_symbol) in ('USDT', 'USDC', 'USDC.E', 'DAI', 'USDE', 'SUSD', 'LUSD', 'USD₮0', 'EURC', 'USDGLO')
                 then 'stablecoin_payments'
            when entity_category in ('lending', 'lending_decentralized')
                 or label_app in ('aave', 'compound', 'moonwell', 'morpho', 'sonne', 'exactly', 'silo', 'extra') then 'lending'
            when entity_category in ('dex', 'dex_aggregator', 'derivative')
                 or label_app in ('uniswap', 'velodrome', 'curve', '1inch', 'odos', 'kyberswap', 'sushiswap', 'balancer', 'velora',
                                  'openocean', 'okx', '0x', 'woofi', 'synthetix', 'perpetual', 'rainbow', 'magpie', 'clipper', 'rango')
                 then 'dex'
            when entity_category in ('bridge', 'cc_communication')
                 or label_app in ('layerzero', 'stargate', 'across', 'hyperlane', 'axelar', 'debridge', 'socket', 'bungee', 'lifi',
                                  'orbiter', 'synapse', 'squid', 'relay', 'mayan', 'eywa', 'omni', 'gaszip', 'rhino-fi', 'everclear',
                                  'xbridge', 'router', 'owlto', 'aptos-pontem-bridge', 'aori')
                 then 'bridge_messaging'
            when entity_category in ('oracle', 'developer_tools', 'erc4337', 'middleware')
                 or label_app in ('chainlink', 'pyth', 'gelato', 'erc4337', 'safe', 'multicall3', 'automata', 'nethermindeth',
                                  'attestationstation', 'ethereum-attestation-service', 'metamask', 'walletconnect')
                 then 'oracle_infra'
            when label_app = 'overtime' then 'other_labeled'  -- prediction market, same segment as the curated 6777c0 factory
            when entity_category in ('gaming', 'gambling', 'community', 'identity', 'airdrop')
                 or label_app in ('farcaster', 'zora', 'opensea', 'xen-crypto', 'xen-crypto-faircrypto', 'worldcoin',
                                  'pooltogether', 'human', 'rabbithole', 'boost', 'dmailofficial', 'sendingme', 'onchaingm', 'paragraph', 'giveth')
                 then 'nft_social'
            when b.address is not null then 'bots_automation'
            when label_app is not null then 'other_labeled'
            else 'unlabeled'
        end as label_segment
    from named n left join bot b using (address)
),
addr as (
    select s.address, coalesce(s.label_app, 'unlabeled-' || substr(s.address, 3)) as label_app,
           coalesce(o.app, s.label_app, 'unlabeled-' || substr(s.address, 3)) as app,
           coalesce(o.segment, s.label_segment) as address_segment,
           case when o.address is not null then 'override' else s.label_source end as source,
           coalesce(f.ttm_fee_usd, 0) as ttm_fee_usd, coalesce(f.all_fee_usd, 0) as all_fee_usd
    from seg s left join address_overrides o using (address) left join fees f using (address)
    union all
    select 'other', 'other', 'other', 'long_tail', 'long_tail', ttm_fee_usd, all_fee_usd
    from fees where address = 'other'
)
-- an app's segment is the segment of its highest-fee address (TTM, then all-time)
select address, app, first(address_segment order by ttm_fee_usd desc, all_fee_usd desc) over (partition by app) as segment,
       source, address_segment, label_app
from addr;

create or replace table m_customer_month as
select a.app, a.segment, date_trunc('month', c.date)::date as month,
       sum(c.total_fee_eth) as fee_eth, sum(c.total_fee_usd) as fee_usd, sum(c.txs)::bigint as txs,
       -- average daily distinct senders over the app's active days, summed over its addresses
       -- (daily uniques are the source's finest grain); same definition as the TTM ranking in notebook 02
       sum(c.distinct_senders) / count(distinct c.date) as senders,
       count(distinct c.to_address) as addresses
from contract_activity c join m_customer_app a on a.address = c.to_address
group by all;
