-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString
-- 4) toDecimal
-- 5) like moved to prewhere
-- 6) completely rewritten correlated subqueries into explicit inner joins

SET partial_merge_join = 1;
SET max_bytes_in_join = 40000000000;
SET enable_debug_queries = 1;
--ANALYZE
select
		s_name,
		s_address
from
(
	select
		s_name,
		s_address,
		s_suppkey
	from
		supplier as s,
		nation as n
	where
		s.s_nationkey = n.n_nationkey
		and toString(n.n_name) = 'CANADA'
) as t1
inner join
(
	SELECT
		sumlq,
		l_partkey,
		l_suppkey,
		ps_availqty
	FROM
	(
	select
		toDecimal32(0.5,2) * sum(l_quantity) as sumlq,
		l_partkey,
		l_suppkey
	from
		lineitem
	where
		l_shipdate >= toDate('1994-01-01')
		and l_shipdate < toDate('1994-01-01') + interval '1' year
	group by l_partkey, l_suppkey
	) as t3
	inner join
	(select
	ps_suppkey,
	ps_availqty
	from
	part as p,
	partsupp as ps
	prewhere
		toString(p.p_name) like 'forest%'
	where
		p.p_partkey = ps.ps_partkey
	) as t4
	on
	t4.ps_suppkey = t3.l_suppkey
) as t2
on
	t2.l_suppkey = t1.s_suppkey
where
	ps_availqty > sumlq
order by
	s_name;
