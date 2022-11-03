# User commands

## user:migrate

This command expect :

1 - A csv file with 2 columns 'email', and 'oldParticipantID'
2 - A yaml file to describe the context

````yaml
    preferredLanguage: 'en'
    studyKeys: [] 
    use2FA: true
```

```csv
email, oldParticipantID
name@example.org, 2030-222b-dfa3-5432
...
```