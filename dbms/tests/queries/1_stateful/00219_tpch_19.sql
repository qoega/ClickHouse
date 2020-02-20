-- 1) FixedString <-> toString
-- 2) toDecimal
-- 3) like moved out from join
-- 4) in moved out from join
select
	sum(l_extendedprice * (1 - l_discount)) as revenue
from
(
select * from
	lineitem as l,
	part as p
where
		p.p_partkey = l.l_partkey
)
where
	(
		toString(p_brand) = 'Brand#12'
		and toString(p_container) in ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')
		and l_quantity >= 1 and l_quantity <= 1 + 10
		and p_size between 1 and 5
		and toString(l_shipmode) in ('AIR', 'AIR REG')
		and toString(l_shipinstruct) = 'DELIVER IN PERSON'
	)
	or
	(
		toString(p_brand) = 'Brand#23'
		and toString(p_container) in ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK')
		and l_quantity >= 10 and l_quantity <= 10 + 10
		and p_size between 1 and 10
		and toString(l_shipmode) in ('AIR', 'AIR REG')
		and toString(l_shipinstruct) = 'DELIVER IN PERSON'
	)
	or
	(
		toString(p_brand) = 'Brand#34'
		and toString(p_container) in ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG')
		and l_quantity >= 20 and l_quantity <= 20 + 10
		and p_size between 1 and 15
		and toString(l_shipmode) in ('AIR', 'AIR REG')
		and toString(l_shipinstruct) = 'DELIVER IN PERSON'
	);
