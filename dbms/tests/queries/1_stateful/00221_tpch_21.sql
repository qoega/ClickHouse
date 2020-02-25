-- 1) FixedString <-> toString
-- 2) rewritten correlated in subqueries explicit inner joins
-- 3) rewritten exists + subquery into explicit any left join
-- 4) set max_threads + max_bytes_before_external_group_by
SET max_bytes_before_external_group_by = 1000000000;
SET max_threads = 5;

select
	s_name,
	count(l_orderkey) as numwait
from
(
	select
		s.s_name as s_name,
		l.l_orderkey as l_orderkey
	from
		lineitem as l,
		orders as o,
		supplier as s,
		nation as n
	where
		s.s_suppkey = l.l_suppkey
		and o.o_orderkey = l.l_orderkey
		and toString(o.o_orderstatus) = 'F'
		and l.l_receiptdate > l.l_commitdate
		and s.s_nationkey = n.n_nationkey
		and toString(n.n_name) = 'SAUDI ARABIA'
) as t3
any left join
(
	select
		l_orderkey
	from
	(
	    select
	        l_orderkey
	    from
	    	lineitem as l1
	    any left join
	        lineitem as l2
	    on
	        l2.l_orderkey = l1.l_orderkey
	    where l2.l_suppkey <> l1.l_suppkey
	) as t1
	any left join
	(
	    select
	        l_orderkey
	    from
	        lineitem as l1
	    any left join
	        lineitem as l3
	    on
	        l3.l_orderkey = l1.l_orderkey
	    where
	        l3.l_suppkey <> l1.l_suppkey
	        and l3.l_receiptdate > l3.l_commitdate
	) as t2
	on t1.l_orderkey = t2.l_orderkey
	where t2.l_orderkey is null
)  as t4
on t3.l_orderkey = t4.l_orderkey
group by
	s_name
order by
	numwait desc,
	s_name
limit 100;
