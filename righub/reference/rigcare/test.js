var RC=require('./assets/logic.js'),a=require('assert');var db=RC.defaults(),v=db.vehicles[0];
a.equal(v.name,'Kenworth');v.odo=24800;var oil=db.reminders[0];a.equal(RC.status(oil,v.odo).state,'due');
v.odo=26000;a.equal(RC.status(oil,v.odo).state,'overdue');a.equal(RC.status(oil,v.odo).milesLeft,-1000);
RC.addLog(db,{vid:v.id,type:'Oil change',date:RC.today(),odo:26500,cost:350.5,notes:''});a.equal(v.odo,26500);a.equal(oil.lastOdo,26500);a.equal(RC.status(oil,v.odo).state,'ok');
var dot={miles:0,days:365,lastOdo:0,lastDate:RC.addDays(RC.today(),-400)};a.equal(RC.status(dot,0).state,'overdue');
dot.lastDate=RC.addDays(RC.today(),-360);a.equal(RC.status(dot,0).state,'due');
RC.addLog(db,{vid:v.id,type:'Tires',date:RC.today(),odo:26600,cost:100,notes:''});var t=RC.totals(db,v.id);a.equal(t.all,450.5);a.equal(t.count,2);
a.ok(RC.validate(JSON.parse(JSON.stringify(db))));a.ok(!RC.validate({}));console.log('all tests passed');
