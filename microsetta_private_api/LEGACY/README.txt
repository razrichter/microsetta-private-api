To generate a new test database:
	python build_db.py

To investigate your new database you can use:
	psql
	\c ag_test			//Switches to the ag_test database
	SET search_path TO ag;		//Switches to the ag schema
	\d				//List tables
  \q

(Note that if you miss any of these, it looks like your database is empty...
but it isn't)

We're not going to worry about backwards compatibility in our patch files while
the system is under development.  This means you may need to wipe your database
and install new patches

This can be done by:

psql
DROP DATABASE ag_test;
\q

python build_db.py
