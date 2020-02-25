-- 1) explicit aliases
-- 2) FixedString <-> toString
-- 3) toDecimal
-- 4) join and group by with having splitted in different select clauses

select
	ps_partkey,
	sum(t1.ps_supplycost * t1.ps_availqty) as value
FROM
(
	SELECT
		ps_partkey,
		ps_supplycost,
		ps_availqty
	from
		partsupp as ps1,
		supplier as s1,
		nation as n1
	where
		ps1.ps_suppkey = s1.s_suppkey
		and s1.s_nationkey = n1.n_nationkey
		and toString(n1.n_name) = 'GERMANY'
) as t1
group by
	t1.ps_partkey having
		sum(t1.ps_supplycost * t1.ps_availqty) > (
			select
				sum(ps.ps_supplycost * ps.ps_availqty) * toDecimal64('0.000002', 10) -- SF=50
			from
				partsupp as ps,
				supplier as s,
				nation as n
			where
				s.s_nationkey = n.n_nationkey
				and toString(n.n_name) = 'GERMANY'
				and ps.ps_suppkey = s.s_suppkey
		)
order by
	value desc;
