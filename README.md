# Audio feed

Any audio file placed in `episodes/` becomes an episode in a podcast feed.

- Feed URL: `https://<your-username>.github.io/<this-repo>/feed.xml`
- Add an episode: upload a file to `episodes/` (web upload or `git push`).
  The feed rebuilds automatically in a minute or two.
- Remove an episode: delete the file from `episodes/`.

Do not rename a file after it has been published: the episode ID is based on
the filename, so a rename makes it look like a new episode and loses its
playback position.

The repository and the published files are public.
