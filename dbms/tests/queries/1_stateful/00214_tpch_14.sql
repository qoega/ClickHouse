-- 1) rewritten date -> toDate
-- 2) toDecimal

select
	toDecimal32(100.00, 2) * sum(case
		when p_type like 'PROMO%'
			then l_extendedprice * (1 - l_discount)
		else 0
	end) / sum(l_extendedprice * (1 - l_discount)) as promo_revenue
from
	lineitem as l,
	part as p
where
	l.l_partkey = p.p_partkey
	and l.l_shipdate >= toDate('1995-09-01')
	and l.l_shipdate < toDate('1995-09-01') + interval '1' month;
