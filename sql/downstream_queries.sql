-- 1. Product analytics: daily payment volume by type
select date(event_ts) as payment_day, payment_type, count(*) as txn_count, sum(amount) as total_amount
from canonical_payments
group by 1, 2
order by 1, 2;

-- 2. Finance: successful AED payments by squad source
select source_system, count(*) as settled_count, sum(amount) as settled_amount_aed
from canonical_payments
where currency = 'AED' and status in ('SETTLED', 'COMPLETED', 'PAID')
group by 1
order by settled_amount_aed desc;

-- 3. Risk: cross-border transfers and card spend outside UAE
select payment_id, payment_type, customer_id, amount, currency, country_code, status
from canonical_payments
where country_code <> 'AE'
order by event_ts desc;

-- 4. CRM: recurring bill-payment customers
select customer_id, count(*) as recurring_bill_count, sum(amount) as recurring_bill_amount
from canonical_payments
where payment_type = 'bill_payment' and is_recurring = 1
group by 1
order by recurring_bill_amount desc;
