-- 1) explicit aliases
-- 3) FixedString <-> toString
-- 4) like moved out from join
-- 5) changed tables order in from expression
select
	nation,
	o_year,
	sum(amount) as sum_profit
from
	(
		select
			n.n_name as nation,
			extract(year from o.o_orderdate) as o_year,
			l.l_extendedprice * (1 - l.l_discount) - ps.ps_supplycost * l.l_quantity as amount,
			p.p_name as p_name
		from
			lineitem as l,
			orders as o,
			part as p,
			supplier as s,
			partsupp as ps,
			nation as n
		where
			s.s_suppkey = l.l_suppkey
			and ps.ps_suppkey = l.l_suppkey
			and ps.ps_partkey = l.l_partkey
			and p.p_partkey = l.l_partkey
			and o.o_orderkey = l.l_orderkey
			and s.s_nationkey = n.n_nationkey
	) as profit
where toString(p_name) like '%green%'
group by
	nation,
	o_year
order by
	nation,
	o_year desc;
