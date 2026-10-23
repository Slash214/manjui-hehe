import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const demo=JSON.parse(readFileSync(process.env.DEMO_FILE ?? '../docs/demo.json','utf8')) as {url:string};
test('sample workspace real login, relogin and screenshots', async ({page})=>{
  await page.goto(demo.url);
  await page.getByLabel('邮箱').fill('demo@manju.local');
  await page.getByLabel('密码').fill('Manju-Local-2026!');
  await page.getByRole('button',{name:'登录工作台'}).click();
  await expect(page.getByLabel('镜头动作')).toHaveValue('掌柜拍桌，催讨房租');
  await expect(page.locator('.shot-card')).toHaveCount(11);
  await page.getByRole('button',{name:'退出登录'}).click();
  await page.getByRole('button',{name:'登录工作台'}).click();
  await expect(page.getByLabel('镜头动作')).toHaveValue('掌柜拍桌，催讨房租');
  for(const size of [{width:1440,height:900},{width:1366,height:768}]){
    await page.setViewportSize(size);
    await page.screenshot({path:`../docs/screenshots/sample-director-${size.width}.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
  await page.getByRole('link',{name:/01.*故事/}).click();
  await expect(page.getByLabel('场次标题',{exact:true})).toHaveValue('饭馆大堂');
  await page.screenshot({path:'../docs/screenshots/sample-story-1366.png',fullPage:true});
  await page.getByRole('link',{name:/02.*资产/}).click();
  await page.getByRole('button',{name:/沈知味/}).click();
  await expect(page.getByRole('heading',{name:'版本历史'})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/sample-assets-1366.png',fullPage:true});
});
