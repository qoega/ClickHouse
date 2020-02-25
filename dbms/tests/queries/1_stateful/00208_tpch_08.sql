-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString
-- 4) changed tables order in from expression
select
	o_year,
	sum(case
		when toString(nation) = 'BRAZIL' then volume
		else 0
	end) / sum(volume) as mkt_share
from
	(
		select
			extract(year from o.o_orderdate) as o_year,
			l.l_extendedprice * (1 - l.l_discount) as volume,
			n2.n_name as nation
		from
			lineitem as l,
			orders as o,
			part as p,
			supplier as s,
			customer as c,
			nation as n1,
			nation as n2,
			region as r
		where
			p.p_partkey = l.l_partkey
			and s.s_suppkey = l.l_suppkey
			and l.l_orderkey = o.o_orderkey
			and o.o_custkey = c.c_custkey
			and c.c_nationkey = n1.n_nationkey
			and n1.n_regionkey = r.r_regionkey
			and toString(r.r_name) = 'AMERICA'
			and s.s_nationkey = n2.n_nationkey
			and o.o_orderdate between toDate('1995-01-01') and toDate('1996-12-31')
			and toString(p.p_type) = 'ECONOMY ANODIZED STEEL'
	) as all_nations
group by
	o_year
order by
	o_year;
