// Estimate remaining runs separately for each offense. Equal-strength teams,
// observed offensive turns, and half a win for a tie.
function estimateWpa(all, isOurTeam) {
  const turns = [];
  const turnAt = all.map((row, i) => {
    if (!i || row.inning !== all[i - 1].inning || isOurTeam(row) !== isOurTeam(all[i - 1])) {
      turns.push(isOurTeam(row));
    }
    return turns.length - 1;
  });
  const distributions = new Map();
  function remainingRuns(outs, runners, currentOuts) {
    const key = [outs, runners, currentOuts].join('/');
    if (distributions.has(key)) return distributions.get(key);
    const mean = outs / 3; // One run per clean half-inning for either team.
    const probs = [Math.exp(-mean)];
    let mass = probs[0];
    for (let k = 1; mass < 1 - 1e-12; k++) {
      probs.push(probs[k - 1] * mean / k);
      mass += probs[k];
    }
    const p = [0.55, 0.38, 0.20][currentOuts];
    for (let i = 0; i < runners; i++) {
      probs.push(0);
      for (let k = probs.length - 1; k >= 0; k--) {
        probs[k] = probs[k] * (1 - p) + (probs[k - 1] || 0) * p;
      }
    }
    distributions.set(key, probs);
    return probs;
  }
  function winChance(i, lead) {
    if (i === all.length) return lead === 0 ? 0.5 : Number(lead > 0);
    const row = all[i], turn = turnAt[i], batting = turns[turn];
    const outsLeft = [0, 0];
    for (let j = turn; j < turns.length; j++) outsLeft[Number(turns[j])] += 3;
    outsLeft[Number(batting)] -= row.outs;
    const ourTeam = remainingRuns(outsLeft[1], batting ? row.runners : 0, row.outs);
    const rival = remainingRuns(outsLeft[0], batting ? 0 : row.runners, row.outs);
    let win = 0;
    for (let a = 0; a < ourTeam.length; a++) {
      for (let b = 0; b < rival.length; b++) {
        const margin = lead + a - b;
        if (margin >= 0) win += ourTeam[a] * rival[b] * (margin ? 1 : 0.5);
      }
    }
    return win;
  }
  let lead = 0;
  const players = new Map();
  const plays = all.map((row, i) => {
    if (row.runs == null || lead == null) { lead = null; return null; }
    const ourTeam = isOurTeam(row);
    const before = winChance(i, lead);
    lead += row.runs * (ourTeam ? 1 : -1);
    const after = winChance(i + 1, lead);
    const value = (after - before) * (ourTeam ? 1 : -1);
    if (row.batter != null) {
      const key = [ourTeam, row.batter].join('/');
      const player = players.get(key) || {ourTeam, batter: row.batter, value: 0};
      player.value += value;
      players.set(key, player);
    }
    return {before: ourTeam ? before : 1 - before, after: ourTeam ? after : 1 - after, value};
  });
  const ranked = [...players.values()].sort((a,b) => b.value - a.value);
  return {plays, ranked};
}
