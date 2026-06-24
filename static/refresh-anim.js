/* refresh-anim.js — server rack / ethernet cable canvas animation */

function initServerCanvas(canvasEl) {
  var W = 360, H = 134;
  canvasEl.width  = W;
  canvasEl.height = H;
  var ctx = canvasEl.getContext('2d');

  /* Read CSS theme colours once */
  var cs = getComputedStyle(document.documentElement);
  function cv(n) { return cs.getPropertyValue(n).trim(); }
  var C = {
    accent:   cv('--accent')   || '#7c88ff',
    good:     cv('--good')     || '#34d399',
    amber:    cv('--amber')    || '#fbbf24',
    warn:     cv('--warn')     || '#f87171',
    border:   cv('--border')   || '#252d40',
    surface2: cv('--surface-2')|| '#1e2436',
    textSub:  cv('--text-sub') || '#7c8db0',
  };

  /* Layout */
  var RX1 = 6,  RX2 = 298;           /* rack left-edge x */
  var RY  = 6,  RW  = 58, RH = 118;  /* rack geometry   */
  var UNITS = 7, UH = 15;            /* server units     */
  var CX1 = RX1 + RW, CX2 = RX2;    /* cable endpoints  */

  /* --- helpers --- */
  function rr(x, y, w, h, r) {       /* rounded rect path */
    ctx.beginPath();
    ctx.moveTo(x+r, y);
    ctx.arcTo(x+w, y,   x+w, y+h, r);
    ctx.arcTo(x+w, y+h, x,   y+h, r);
    ctx.arcTo(x,   y+h, x,   y,   r);
    ctx.arcTo(x,   y,   x+w, y,   r);
    ctx.closePath();
  }

  /* --- state --- */
  function makeLeds() {
    return Array.from({length: UNITS}, function(_, i) {
      return { on: Math.random() > 0.15,
               color: Math.random() > 0.25 ? C.good : C.amber,
               phase: Math.random() * Math.PI * 2,
               fill:  Math.random() };
    });
  }
  var ledsL = makeLeds(), ledsR = makeLeds();

  var cables = Array.from({length: UNITS}, function(_, i) {
    return { y: RY + i * UH + UH * 0.55,
             active: Math.random() > 0.2,
             load: Math.random(),
             color: [C.accent, C.good, C.accent, C.amber][i % 4] };
  });

  var packets = [];

  /* --- spawn a data packet on an active cable --- */
  function spawnPacket() {
    var alive = cables.filter(function(c){ return c.active; });
    if (!alive.length) return;
    var cab = alive[Math.floor(Math.random() * alive.length)];
    var dir = Math.random() > 0.12 ? 1 : -1;
    packets.push({
      x:     dir > 0 ? CX1 + 2 : CX2 - 2,
      y:     cab.y + (Math.random() - 0.5) * 2,
      dir:   dir,
      speed: 1.4 + Math.random() * 2.8,
      color: cab.color,
      w:     3 + Math.random() * 6,
      h:     1.5,
    });
  }

  /* --- draw one rack --- */
  function drawRack(rx, leds, flip) {
    /* body */
    ctx.fillStyle = C.surface2;
    rr(rx, RY, RW, RH, 4); ctx.fill();
    ctx.strokeStyle = C.border; ctx.lineWidth = 1;
    rr(rx, RY, RW, RH, 4); ctx.stroke();

    /* mounting rail ears */
    ctx.fillStyle = C.border;
    ctx.fillRect(rx + 2, RY + 4, 4, 2);
    ctx.fillRect(rx + RW - 6, RY + 4, 4, 2);
    ctx.fillRect(rx + 2, RY + RH - 6, 4, 2);
    ctx.fillRect(rx + RW - 6, RY + RH - 6, 4, 2);

    for (var i = 0; i < UNITS; i++) {
      var uy = RY + i * UH + 2;
      var led = leds[i];

      /* unit slot background */
      ctx.fillStyle = C.border;
      ctx.globalAlpha = 0.35;
      rr(rx + 4, uy + 1, RW - 8, UH - 3, 2); ctx.fill();
      ctx.globalAlpha = 1;

      /* LED dot with glow */
      var pulse = led.on
        ? 0.55 + 0.45 * Math.sin(frame * 0.07 + led.phase)
        : 0.12;
      ctx.fillStyle = led.color;
      ctx.globalAlpha = pulse;
      ctx.shadowColor = led.color;
      ctx.shadowBlur  = led.on ? 7 : 0;
      var lx = flip ? rx + RW - 10 : rx + 8;
      ctx.beginPath();
      ctx.arc(lx, uy + UH * 0.45, 2.8, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;

      /* activity bar */
      var bx = flip ? rx + 6        : rx + 15;
      var bw = RW - 22;
      ctx.fillStyle = C.border;
      ctx.fillRect(bx, uy + 5, bw, 2.5);
      var barFill = led.on
        ? 0.25 + 0.75 * Math.abs(Math.sin(frame * 0.045 + led.phase * 1.7))
        : 0.08;
      ctx.fillStyle = led.color;
      ctx.globalAlpha = 0.65;
      ctx.fillRect(bx, uy + 5, bw * barFill, 2.5);
      ctx.globalAlpha = 1;

      /* port nub on rack edge (where cable plugs in) */
      var px = flip ? rx : rx + RW - 4;
      ctx.fillStyle = cables[i] && cables[i].active ? C.accent : C.border;
      ctx.globalAlpha = 0.9;
      ctx.fillRect(px, uy + 4, 4, 5);
      ctx.globalAlpha = 1;
    }
  }

  /* --- draw cables --- */
  function drawCables() {
    cables.forEach(function(cab) {
      if (!cab.active) return;
      var sag = 1.5 + cab.load * 5;
      var mx  = (CX1 + CX2) / 2;
      ctx.beginPath();
      ctx.moveTo(CX1, cab.y);
      ctx.bezierCurveTo(mx - 30, cab.y + sag, mx + 30, cab.y + sag, CX2, cab.y);
      ctx.strokeStyle = cab.color;
      ctx.lineWidth   = 1.5;
      ctx.globalAlpha = 0.18 + cab.load * 0.22;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });
  }

  /* --- draw packets --- */
  function drawPackets() {
    packets = packets.filter(function(p) {
      p.x += p.speed * p.dir;
      var alive = p.dir > 0 ? p.x < CX2 - 2 : p.x > CX1 + 2;
      if (alive) {
        ctx.fillStyle   = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur  = 6;
        ctx.globalAlpha = 0.95;
        ctx.fillRect(p.x - p.w / 2, p.y - p.h / 2, p.w, p.h);
        ctx.shadowBlur  = 0;
        ctx.globalAlpha = 1;
      }
      return alive;
    });
  }

  /* --- throughput readout in the middle gap --- */
  function drawMeta() {
    var activeN = cables.filter(function(c){ return c.active; }).length;
    var mbps = (activeN * 11.3 + Math.sin(frame * 0.09) * 2.4 + Math.random() * 0.8).toFixed(1);
    ctx.fillStyle   = C.textSub;
    ctx.font        = '9px "Courier New", monospace';
    ctx.textAlign   = 'center';
    ctx.globalAlpha = 0.55;
    ctx.fillText(mbps + ' MB/s', W / 2, RY + RH + 12);
    ctx.globalAlpha = 1;

    /* rack labels */
    ctx.fillStyle   = C.textSub;
    ctx.globalAlpha = 0.4;
    ctx.fillText('SRV-01', RX1 + RW / 2, RY + RH + 12);
    ctx.fillText('SRV-02', RX2 + RW / 2, RY + RH + 12);
    ctx.globalAlpha = 1;
  }

  /* --- main loop --- */
  var frame = 0;
  var raf;

  function tick() {
    frame++;
    ctx.clearRect(0, 0, W, H);

    /* Phase shift every ~8 s (200 frames @ ~25 fps) */
    if (frame % 200 === 0) {
      cables.forEach(function(c) {
        if (Math.random() > 0.45) {
          c.active = Math.random() > 0.18;
          c.load   = Math.random();
        }
      });
      [ledsL, ledsR].forEach(function(leds) {
        leds.forEach(function(l) {
          if (Math.random() > 0.5) l.on = Math.random() > 0.12;
        });
      });
    }

    /* Random LED flicker */
    if (frame % 22 === 0) {
      [ledsL, ledsR].forEach(function(leds) {
        leds.forEach(function(l) {
          if (Math.random() > 0.88) l.on = !l.on;
        });
      });
    }

    drawCables();

    /* Spawn packets */
    if (frame % 11 === 0) spawnPacket();
    if (frame % 28 === 0 && Math.random() > 0.4) spawnPacket();

    drawPackets();
    drawRack(RX1, ledsL, false);
    drawRack(RX2, ledsR, true);
    drawMeta();

    raf = requestAnimationFrame(tick);
  }

  tick();
  return function stop() { cancelAnimationFrame(raf); };
}
