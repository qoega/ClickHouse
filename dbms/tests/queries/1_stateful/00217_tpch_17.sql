-- 1) FixedString <-> toString
-- 2) toDecimal
-- 3) explicit aliases
-- 4) completely rewritten correlated subqueries into explicit inner joins
select
	sum(l_extendedprice) / toDecimal32(7.0, 2) as avg_yearly
from
(
	select *
	from
		lineitem as l,
		part as p
	where
		p.p_partkey = l.l_partkey
		and toString(p.p_brand) = 'Brand#23'
		and toString(p.p_container) = 'MED BOX'
) as t1
inner join
(
	select
		toDecimal32(0.2, 2) * avg(l_quantity) as qty,
		l_partkey
	from
		lineitem
	group by
		l_partkey
) as t2
on
	t2.l_partkey = t1.l_partkey
where
	t1.l_quantity < t2.qty
