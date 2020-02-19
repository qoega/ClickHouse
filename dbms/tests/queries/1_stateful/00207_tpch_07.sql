-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString in where
-- 4) OR moved out of join query to separate select
-- 5) changed tables order in from expression
select
	supp_nation,
	cust_nation,
	l_year,
	sum(volume) as revenue
from
(
select *
from
	(
		select
			n1.n_name as supp_nation,
			n2.n_name as cust_nation,
			extract(year from l.l_shipdate) as l_year,
			l.l_extendedprice * (1 - l.l_discount) as volume
		from
			lineitem as l,
			supplier as s,
			orders as o,
			customer as c,
			nation as n1,
			nation as n2
		where
			s.s_suppkey = l.l_suppkey
			and o.o_orderkey = l.l_orderkey
			and c.c_custkey = o.o_custkey
			and s.s_nationkey = n1.n_nationkey
			and c.c_nationkey = n2.n_nationkey
			and l.l_shipdate between toDate('1995-01-01') and toDate('1996-12-31')
	)
	where
		(toString(supp_nation) = 'FRANCE' and toString(cust_nation) = 'GERMANY')
		or (toString(supp_nation) = 'GERMANY' and toString(cust_nation) = 'FRANCE')
) as shipping
group by
	supp_nation,
	cust_nation,
	l_year
order by
	supp_nation,
	cust_nation,
	l_year;
