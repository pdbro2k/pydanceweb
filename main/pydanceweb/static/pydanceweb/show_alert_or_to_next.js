let adjudicators = document.getElementsByTagName("dd")[1].textContent.replace(/\s/g, "").split(",");

let sums = {};
let trs = document.getElementsByTagName("tbody")[0].getElementsByTagName("tr");
for (let i=0; i<trs.length; ++i) {
  let tds = trs[i].getElementsByTagName("td");
  for (let j=0; j<adjudicators.length; ++j) {
    let td = parseInt(tds[j].innerHTML);
    if (adjudicators[j] in sums) {
      sums[adjudicators[j]] = sums[adjudicators[j]] + td;
    } else {
      sums[adjudicators[j]] = td;
    }
  }
}

let missingAdjudicators = [];
Object.entries(sums).forEach(function([key, value]) {
  if (value == 0) {
    missingAdjudicators.push(key);
  }
});

if (missingAdjudicators.length > 0) {
  document.getElementById("missing_adjudicators").innerHTML = missingAdjudicators;
  document.getElementById("to_next").style.display = "None";
} else {
  document.getElementById("missing_adjudicators_alert").style.display = "None";
}
