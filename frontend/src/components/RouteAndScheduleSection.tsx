import React from 'react';

export const RouteAndScheduleSection: React.FC = () => {
  const schedule = [
    { time: '04:30 AM', title: 'Gates & Baggage Counters Open', desc: 'Secure luggage drop and bib verification.' },
    { time: '05:00 AM', title: 'Official Warm-up & Zumba', desc: 'Pre-race dynamic mobility with fitness trainers.' },
    { time: '05:30 AM', title: '21K Half Marathon Flag-off', desc: 'Pacer waves line-up and gun start.' },
    { time: '06:00 AM', title: '10K Timed Run Flag-off', desc: 'Elite runners & open category start.' },
    { time: '06:30 AM', title: '5K Fun Run Flag-off', desc: 'Beginner, corporate, and family wave start.' },
    { time: '08:30 AM', title: 'Podium & Awards Ceremony', desc: 'Trophies, prize money distribution & breakfast.' },
  ];

  return (
    <section id="schedule" className="py-16 sm:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12 transition-colors">
      
      {/* Section Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold uppercase tracking-wider border border-amber-200">
          Race Day Details
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Schedule & Certified Route
        </h2>
        <p className="text-slate-600 text-sm">
          Plan your morning. Seamless logistics from car parking to the finish line chute.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        
        {/* Timeline */}
        <div className="bg-white border border-slate-200 shadow-sm rounded-3xl p-6 sm:p-8 space-y-6">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <span>⏰</span> Race Day Timeline (Sunday, Oct 18)
          </h3>

          <div className="space-y-4 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200">
            {schedule.map((item, idx) => (
              <div key={idx} className="relative flex items-start gap-4 pl-8">
                <div className="absolute left-2 top-1.5 w-3.5 h-3.5 rounded-full bg-amber-500 ring-4 ring-white -translate-x-1/2 shadow-sm" />
                <div>
                  <div className="font-mono text-xs font-bold text-amber-600">{item.time}</div>
                  <div className="font-bold text-slate-900 text-sm mt-0.5">{item.title}</div>
                  <div className="text-xs text-slate-600">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Route Highlights Card */}
        <div className="bg-white border border-slate-200 shadow-sm rounded-3xl p-6 sm:p-8 space-y-6">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <span>🗺️</span> Course & Elevation Highlights
          </h3>

          <div className="space-y-4 text-xs text-slate-700">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex justify-between font-semibold text-slate-900">
                <span>Start & Finish Arena:</span>
                <span className="text-amber-600 font-bold">Kanteerava Stadium Track</span>
              </div>
              <p className="text-slate-600">
                Lush green Cubbon Park loops transitioning to wide, asphalted boulevard expressways with zero vehicular traffic.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500 font-medium">Max Elevation Gain</div>
                <div className="text-xl font-extrabold text-emerald-600 mt-1">28 Meters</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Ultra-flat PB Course</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500 font-medium">Hydration Stations</div>
                <div className="text-xl font-extrabold text-amber-600 mt-1">Every 1.5 KM</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Water, Ice & Fast Gels</div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900">
              💡 <strong>Bib Expo Collection:</strong> Registered participants can collect race kits at the Kanteerava Expo Arena on Oct 16 & 17 from 10:00 AM to 06:00 PM.
            </div>
          </div>
        </div>

      </div>

    </section>
  );
};
