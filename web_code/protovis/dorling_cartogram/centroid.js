function area(pts) {
   var area=0;
   var nPts = pts.length;
   var j=nPts-1;
   var p1; var p2;

   for (var i=0;i<nPts;j=i++) {
      p1=pts[i]; p2=pts[j];
      area+=p1.lng*p2.lat;
      area-=p1.lat*p2.lng;
   }
   area/=2;
   return area;
}

function centroid(pts) {
   var nPts = pts.length;
   var lng=0; var lat=0;
   var f;
   var j=nPts-1;
   var p1; var p2;

   for (var i=0;i<nPts;j=i++) {
      p1=pts[i]; p2=pts[j];
      f=p1.lng*p2.lat-p2.lng*p1.lat;
      lng+=(p1.lng+p2.lng)*f;
      lat+=(p1.lat+p2.lat)*f;
   }

   f=area(pts)*6;
   return {lng:lng/f, lat:lat/f};
}