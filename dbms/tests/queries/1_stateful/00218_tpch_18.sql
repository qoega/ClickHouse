-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) rewritten correlated in subqueries explicit inner joins

select
	c_name,
	c_custkey,
	o_orderkey,
	o_orderdate,
	o_totalprice,
	sum(sumlq)
from
(
	select
		c_name,
		c_custkey,
		o_orderkey,
		o_orderdate,
		o_totalprice
	from
		orders as o,
		customer as c
	where
		c.c_custkey = o.o_custkey
) as t1
inner join
(
	select
		l_orderkey,
		sum(l_quantity) as sumlq
	from
		lineitem
	group by
		l_orderkey having
			sum(l_quantity) > 300
) as t2
on t2.l_orderkey = t1.o_orderkey
group by
	c_name,
	c_custkey,
	o_orderkey,
	o_orderdate,
	o_totalprice
order by
	o_totalprice desc,
	o_orderdate
limit 100;
