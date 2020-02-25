-- 1) rewritten date -> toDate
-- 2) toDecimal
select
	sum(l_extendedprice * l_discount) as revenue
from
	lineitem
where
	l_shipdate >= toDate('1994-01-01')
	and l_shipdate < toDate('1994-01-01') + interval '1' year
	and l_discount between toDecimal32(0.06, 2) - toDecimal32(0.01, 2) and toDecimal32(0.06, 2) + toDecimal32(0.01, 2)
	and l_quantity < 24;
