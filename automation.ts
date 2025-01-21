import { test, expect } from '@playwright/test';

test('successful login', async ({ page }) => {

    await page.goto('https://tamiltranslator.pythonanywhere.com/login');


    await page.fill('input[name="username"]', 'test55');

    await page.click('button[type="submit"]');


    await expect(page).toHaveURL('https://tamiltranslator.pythonanywhere.com/');


    await page.fill('textarea[name="text"]', 'After translating the text, clear the history. If you try to translate again, it still shows the previous text.');


    await page.selectOption('select[name="src_lang"]', 'en');

    await page.selectOption('select[name="dest_lang"]', 'ta');


    await page.click('button[type="submit"]');


    const translation = page.locator('#translatedText');

    await expect(translation).toHaveText('உரையை மொழிபெயர்த்த பிறகு, வரலாற்றை அழிக்கவும்.நீங்கள் மீண்டும் மொழிபெயர்க்க முயற்சித்தால், அது முந்தைய உரையை இன்னும் காட்டுகிறது.');

    console.log('Translation test passed!');


    console.log('Login test passed!');
});
