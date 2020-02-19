-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) correlated subquery rewritten to explicit left join with aggregation
-- 4) FixedString <-> toString in where
-- 5) like moved out of join query

select
	s_acctbal,
	s_name,
	n_name,
	p_partkey,
	p_mfgr,
	s_address,
	s_phone,
	s_comment,
	s_suppkey
from
(
	select
		ps1.ps_suppkey as ps_suppkey,
		n1.n_nationkey as n_nationkey,
		n1.n_regionkey as n_regionkey,
		s1.s_acctbal as s_acctbal,
		s1.s_name as s_name,
		n1.n_name as n_name,
		s1.s_address as s_address,
		s1.s_phone as s_phone,
		s1.s_comment as s_comment,
		s1.s_suppkey as s_suppkey,
		p1.p_mfgr as p_mfgr,
		p1.p_partkey as p_partkey
	from
		partsupp as ps1,
		supplier as s1,
		nation as n1,
		part as p1,
		region as r1
	where
		s1.s_suppkey = ps1.ps_suppkey
		and s1.s_nationkey = n1.n_nationkey
		and n1.n_regionkey = r1.r_regionkey
		and p1.p_partkey = ps1.ps_partkey
		and p1.p_size = 15
) as t1
ANY LEFT JOIN
(
	select
		min(ps_supplycost) as min_cost,
		ps2.ps_suppkey as ps_suppkey
	from
		partsupp as ps2,
		supplier as s2,
		nation as n2,
		region as r2
	where
		s2.s_suppkey = ps2.ps_suppkey
		and s2.s_nationkey = n2.n_nationkey
		and n2.n_regionkey = r2.r_regionkey
		and r2.r_name = toFixedString('EUROPE', 25)
	group by
		ps_suppkey
) as t2
on t1.ps_suppkey = t2.ps_suppkey
where p_type like '%BRASS'
order by
	s_acctbal desc,
	n_name,
	s_name,
	p_partkey
limit 100;
