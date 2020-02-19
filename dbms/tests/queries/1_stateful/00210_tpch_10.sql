-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString in where
-- 4) OR moved out of join query to separate select
-- 5) changed tables order in from expression
select
	c.c_custkey as c_custkey,
	c.c_name as c_name,
	sum(l.l_extendedprice * (1 - l.l_discount)) as revenue,
	c.c_acctbal as c_acctbal,
	n.n_name as n_name,
	c.c_address as c_address,
	c.c_phone as c_phone,
	c.c_comment as c_comment
from
	customer as c,
	orders as o,
	lineitem as l,
	nation as n
where
	c.c_custkey = o.o_custkey
	and l.l_orderkey = o.o_orderkey
	and o.o_orderdate >= toDate('1993-10-01')
	and o.o_orderdate < toDate('1993-10-01') + interval '3' month
	and toString(l.l_returnflag) = 'R'
	and c.c_nationkey = n.n_nationkey
group by
	c_custkey,
	c_name,
	c_acctbal,
	c_phone,
	n_name,
	c_address,
	c_comment
order by
	revenue desc
limit 20;
