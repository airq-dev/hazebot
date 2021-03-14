# Translations

We currently also offer hazebot in Spanish, and have built the tooling to expand langugage offerings with additional interest or contributions. Our current process is a bit clunky and we welcome contributions to improve the process or translation quality. 

As we currently constructed, if you add in new strings (i.e. new commands) you must add in a corresponding translation or it will break the non-english services. 

We use http://babel.pocoo.org/en/latest/index.html to wrap strings and https://poeditor.com/ to manage our translation library. You must translate the strings themselves into the non-english langugae. Ideally we would have a bilingual volunteer lead the translation efforts, but Google Translate works for most cases. 

Translation documents are found in the translation folder, with a corresponding .mo and .po file for each language. You can edit this file directly, but you must generate a new .mo file using the babel `compile`
command. 

###To Support Existing Spanish Services Using PoE editor 
1. You'll need an account with poeeditor. Ping Ian or Will and we can add you to the hazebot Spanish project. 
2. Pip install babel 
3. Make sure that all strings that are functionc alls are wrapped with `gettext`. For strings that are not functions, you will need to use `lazy_gettext`. 
4. After you finish updating, run the pybabel `extract` command
5. Upload this file into PoE editor, which will automatically track new strings added/changed. For strings that do not have translations, you will be prompted to add one in. 
6. After completing this step, download the new .po file from poe editor. Run the babel `compile`
command to generate a .mo file. 
7. Run hazebot locally to check your translations and then commit.  

###To Add a New Language 
1. Got an idea for a new language? Ping Ian or Will. We want to make sure that hazebot is accessible to all, but we have found that new langugaes does slow down our velocity.
