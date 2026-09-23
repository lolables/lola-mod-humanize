auth: switch password validation to bcrypt, clean up sessions

- Replace plaintext password comparison with bcrypt in `authenticate_user`
- Wire session management (cookies + JWT) through the new auth flow
- Remove dead `check_password` function
- Add tests for the new auth path
