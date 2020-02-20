-- 1) rewritten date -> toDate
-- 2) rewritten alias
-- 3) explicit aliases
-- 3) drop view -> drop table
create view revenue0 as
 	select
 		l_suppkey as supplier_no,
 		sum(l_extendedprice * (1 - l_discount)) as total_revenue
 	from
 		lineitem
 	where
 		l_shipdate >= toDate('1996-01-01')
 		and l_shipdate < toDate('1996-01-01') + interval '3' month
 	group by
 		l_suppkey;

select
	s_suppkey,
	s_name,
	s_address,
	s_phone,
	total_revenue
from
	supplier as s,
	revenue0 as r
where
	s.s_suppkey = r.supplier_no
	and r.total_revenue = (
		select
			max(total_revenue)
		from
			revenue0
	)
order by
	s_suppkey;
drop table revenue0;
