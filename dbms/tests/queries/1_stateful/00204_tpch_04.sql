-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 5) rewritten exists + subquery into explicit any left join
select
	o_orderpriority,
	count(*) as order_count
from
	orders
any left join
(
	select
		o_orderkey
	from
		lineitem as l,
		orders as o
	where
		l.l_orderkey = o.o_orderkey
		and	l.l_commitdate < l.l_receiptdate
) as t2
ON orders.o_orderkey = t2.o_orderkey
where
	o_orderdate >= toDate('1993-07-01')
	and o_orderdate < toDate('1993-07-01') + interval '3' month
group by
	o_orderpriority
order by
	o_orderpriority;
