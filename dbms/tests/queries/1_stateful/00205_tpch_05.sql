-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString in where
-- 4) like moved out of join query
-- 5) changed tables order in from expression
select
	n_name,
	sum(l.l_extendedprice * (1 - l.l_discount)) as revenue
from
	lineitem as l,
	orders as o,
	customer as c,
	supplier as s,
	nation as n,
	region as r
where
	c.c_custkey = o.o_custkey
	and l.l_orderkey = o.o_orderkey
	and l.l_suppkey = s.s_suppkey
	and c.c_nationkey = s.s_nationkey
	and s.s_nationkey = n.n_nationkey
	and n.n_regionkey = r.r_regionkey
	and toString(r.r_name) = 'ASIA'
	and o.o_orderdate >=  toDate('1994-01-01')
	and o.o_orderdate < toDate('1994-01-01') + interval '1' year
group by
	n_name
order by
	revenue desc;
