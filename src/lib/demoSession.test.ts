import { describe, expect, it } from 'vitest';

import { DEMO_USER, checkDemoCredentials, initials, parseDemoSession } from './demoSession';

describe('checkDemoCredentials', () => {
  it('acepta la cuenta de demostración, sin distinguir mayúsculas en el correo', () => {
    expect(checkDemoCredentials(DEMO_USER.email.toUpperCase(), DEMO_USER.password)).toBe(true);
  });

  it('rechaza otra contraseña o correo', () => {
    expect(checkDemoCredentials(DEMO_USER.email, 'otra')).toBe(false);
    expect(checkDemoCredentials('otro@correo.test', DEMO_USER.password)).toBe(false);
  });
});

describe('parseDemoSession', () => {
  it('devuelve la sesión solo si pertenece al usuario demo', () => {
    const valid = JSON.stringify({ email: DEMO_USER.email, name: DEMO_USER.name, startedAt: '2026-10-15T00:00:00Z' });
    expect(parseDemoSession(valid)?.name).toBe(DEMO_USER.name);
    expect(parseDemoSession(JSON.stringify({ email: 'x@y.z', name: 'x', startedAt: '' }))).toBeNull();
  });

  it('tolera datos corruptos o ausentes', () => {
    expect(parseDemoSession(null)).toBeNull();
    expect(parseDemoSession('{no-json')).toBeNull();
  });
});

describe('initials', () => {
  it('toma la inicial de los dos primeros nombres', () => {
    expect(initials('Lucía Mendoza Quispe')).toBe('LM');
    expect(initials('  ana  ')).toBe('A');
  });
});
