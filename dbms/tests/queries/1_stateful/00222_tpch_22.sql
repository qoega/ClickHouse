-- 1) rewrite not exists into join + where is null
-- 2) enable join_use_nulls
-- 3) toDecimal
-- 4) explicit aliases

SET join_use_nulls = 1;
select
	cntrycode,
	count(*) as numcust,
	sum(c_acctbal) as totacctbal
from
	(
		select
			substring(c_phone from 1 for 2) as cntrycode,
			c_acctbal
		from
			customer as c
		left join
			orders as o
		on o.o_custkey = c.c_custkey
		where
			o.o_custkey is null
			and substring(c.c_phone from 1 for 2) in
				('13', '31', '23', '29', '30', '18', '17')
			and c.c_acctbal > (
				select
					avg(c.c_acctbal)
				from
					customer as c
				where
					c.c_acctbal > toDecimal32(0.00, 2)
					and substring(c.c_phone from 1 for 2) in
						('13', '31', '23', '29', '30', '18', '17')
			)
	) as custsale
group by
	cntrycode
order by
	cntrycode;
