-- 1) FixedString <-> toString
-- 2) like moved out from join
-- 3) in moved out from join
-- 4) explicit aliases
select * from
(
	select
		p.p_brand as p_brand,
		p.p_type as p_type,
		p.p_size as p_size,
		count(distinct ps.ps_suppkey) as supplier_cnt
	from
		partsupp as ps,
		part as p
	where
		p.p_partkey = ps.ps_partkey
		and toString(p.p_brand) <> 'Brand#45'
		and ps.ps_suppkey not in (
			select
				s_suppkey
			from
				supplier
			where
				toString(s_comment) like '%Customer%Complaints%'
		)
	group by
		p_brand,
		p_type,
		p_size
	order by
		supplier_cnt desc,
		p_brand,
		p_type,
		p_size
)
where
	toString(p_type) not like 'MEDIUM POLISHED%'
	and p_size in (49, 14, 23, 45, 19, 3, 36, 9)
