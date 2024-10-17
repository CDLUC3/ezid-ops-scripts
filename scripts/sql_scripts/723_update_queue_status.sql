# UNIX_TIMESTAMP('2023-06-29 05:10:00')=1688040600
# the 'O' status was implemented on 2023-06-29 shortly after 5am.
# update old records with 'S' status to 'O' so the async cleanup job can pick them up 
 
update ezidapp_datacitequeue
set status = 'O'
where enqueuetime<1688040600  and status='S';

update ezidapp_searchindexerqueue
set status = 'O'
where enqueuetime<1688040600 and status = 'S';

