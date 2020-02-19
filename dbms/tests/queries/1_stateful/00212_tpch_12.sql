-- 1) rewritten date -> toDate
-- 2) explicit aliases
-- 3) FixedString <-> toString
-- 4) in moved out of where to prewhere
-- 5) changed tables order in from expression
select
	l.l_shipmode as l_shipmode,
	sum(case
		when toString(o.o_orderpriority) = '1-URGENT'
			or toString(o.o_orderpriority) = '2-HIGH'
			then 1
		else 0
	end) as high_line_count,
	sum(case
		when toString(o.o_orderpriority) <> '1-URGENT'
			and toString(o.o_orderpriority) <> '2-HIGH'
			then 1
		else 0
	end) as low_line_count
from
	lineitem as l,
	orders as o
prewhere
	toString(l.l_shipmode) in ('MAIL', 'SHIP')
where
	o.o_orderkey = l.l_orderkey
	and l.l_commitdate < l.l_receiptdate
	and l.l_shipdate < l.l_commitdate
	and l.l_receiptdate >= toDate('1994-01-01')
	and l.l_receiptdate < toDate('1994-01-01') + interval '1' year
group by
	l.l_shipmode
order by
	l.l_shipmode;
