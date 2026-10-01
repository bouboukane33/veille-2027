import { test, expect, type Page } from '@playwright/test';

async function openDemo(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explorer l’aperçu fictif' }).click();
  await expect(page.locator('.mode-badge')).toHaveText('DEMO / FICTIF');
  await expect(
    page.locator('.kpi-card').filter({ hasText: 'Articles analysés' }).locator('.kpi-value'),
  ).toHaveText('100');
}

test('real data is the default and missing storage never becomes fabricated data', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.locator('.mode-badge')).toHaveText('Données réelles');
  await expect(
    page.getByRole('heading', { name: 'Connecter votre espace de veille' }),
  ).toBeVisible();
  await expect(page.locator('.kpi-card')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Exporter les données' })).toBeDisabled();
});

test('demo navigation, personality, themes, content filters and CSV download work', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await openDemo(page);
  await expect(
    page.locator('.kpi-card').filter({ hasText: 'Vidéos analysées' }).locator('.kpi-value'),
  ).toHaveText('40');
  await page.getByRole('link', { name: 'Personnalités', exact: true }).click();
  await expect(page.locator('.person-table tbody tr')).toHaveCount(10);
  await page.getByRole('button', { name: 'Fiche de Gabriel Attal' }).click();
  await expect(page.locator('.brief-hero h2')).toHaveText('Gabriel Attal');
  await page.getByRole('link', { name: 'Actualités', exact: true }).click();
  await page.getByLabel('Personnalité', { exact: true }).selectOption('all');
  await page.getByLabel('Rechercher un contenu').fill('Gabriel Attal');
  await expect(page.locator('.activity-item')).toHaveCount(11);
  await page.getByLabel('Type de contenu').selectOption('youtube');
  await expect(page.locator('.activity-item')).toHaveCount(3);
  await page.getByLabel('Rechercher un contenu').fill('texte introuvable 123456');
  await expect(page.getByText('Aucun contenu ne correspond à ces filtres.')).toBeVisible();
  await page.getByRole('link', { name: 'Thématiques CCR', exact: true }).click();
  await expect(page.locator('.topic-card')).toHaveCount(10);
  await expect(page.locator('.matrix tbody tr')).toHaveCount(10);
  await page.getByRole('button', { name: 'Exporter les données' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /^personalities\.csv / }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('personalities.csv');
  await page.getByRole('button', { name: 'Fermer les exports' }).click();
  expect(errors).toEqual([]);
});

test('mobile dashboard fits viewport and navigation remains usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openDemo(page);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.getByRole('button', { name: 'Ouvrir le menu' }).click();
  await page.getByRole('link', { name: 'Actualités', exact: true }).click();
  await expect(page.getByLabel('Rechercher un contenu')).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});

test('the demo cannot open external fictitious sources or trigger collection', async ({ page }) => {
  await openDemo(page);
  await page.getByRole('link', { name: 'Actualités', exact: true }).click();
  await expect(page.locator('a[href*="example.invalid"]')).toHaveCount(0);
  await page.getByRole('link', { name: 'Sources & méthode', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Lancer une collecte réelle' })).toBeDisabled();
});
