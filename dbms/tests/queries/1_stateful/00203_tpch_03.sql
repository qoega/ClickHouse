-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString
-- 4) like moved out from join
-- 5) changed tables order in from expression

select
	l.l_orderkey as l_orderkey,
	sum(l.l_extendedprice * (1 - l.l_discount)) as revenue,
	o.o_orderdate as o_orderdate,
	o.o_shippriority as o_shippriority
from
	lineitem as l,
	orders as o,
	customer as c
where
	c.c_custkey = o.o_custkey
	and l.l_orderkey = o.o_orderkey
	and toString(c.c_mktsegment) = 'BUILDING'
	and o.o_orderdate < toDate('1995-03-15')
	and l.l_shipdate > toDate('1995-03-15')
group by
	l_orderkey,
	o_orderdate,
	o_shippriority
order by
	revenue desc,
	o_orderdate
limit 10;