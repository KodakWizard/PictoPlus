
<p align="center">
  <img src="docs/images/icon-128.png" width="100" alt="PictoPlus logo">
</p>

<h1 align="center">PictoPlus</h1>

<p align="center">
  Make your own puzzles for Picross 3D: Round 2.
</p>

<p align="center">
  Create puzzles, import 3D models and build custom books to play on your Nintendo 3DS or Azahar.
</p>

<p align="center">
  <a href="https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-Windows.zip"><strong>Windows Editor</strong></a>
  &nbsp; · &nbsp;
  <a href="https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-SD-Loader.zip"><strong>3DS / Azahar Loader</strong></a>
  &nbsp; · &nbsp;
  <a href="https://github.com/KodakWizard/PictoPlus/releases/tag/v1.0.0">v1.0.0 Release</a>
</p>

---

Ever wished Picross 3D: Round 2 had more puzzles?

PictoPlus is a little fan-made editor I've been working on that lets you create your own puzzles, turn 3D models into puzzles and put everything into custom books. You can play them yourself or share them with other people.

## Screenshots

**Windows editor**

<table>
  <tr>
    <td width="50%">
      <a href="docs/images/PictoPlusApp-1.png">
        <img src="docs/images/PictoPlusApp-1.png" width="100%" alt="PictoPlus puzzle designer">
      </a>
    </td>
    <td width="50%">
      <a href="docs/images/PictoPlusApp-2.png">
        <img src="docs/images/PictoPlusApp-2.png" width="100%" alt="PictoPlus 3D model preview">
      </a>
    </td>
  </tr>
</table>

**In-game**

<table>
  <tr>
    <td width="50%">
      <a href="docs/images/3DS-2.png">
        <img src="docs/images/3DS-2.png" width="100%" alt="Custom Animals puzzle book">
      </a>
    </td>
    <td width="50%">
      <a href="docs/images/3DS-3.png">
        <img src="docs/images/3DS-3.png" width="100%" alt="Completed seahorse puzzle">
      </a>
    </td>
  </tr>
</table>

<details>
<summary>More screenshots</summary>

**Windows editor**

<table>
  <tr>
    <td width="50%">
      <a href="docs/images/PictoPlusApp-3.png">
        <img src="docs/images/PictoPlusApp-3.png" width="100%" alt="Difficulty editor">
      </a>
    </td>
    <td width="50%">
      <a href="docs/images/PictoPlusApp-4.png">
        <img src="docs/images/PictoPlusApp-4.png" width="100%" alt="Book library">
      </a>
    </td>
  </tr>
</table>

**In-game**

<table>
  <tr>
    <td width="50%">
      <a href="docs/images/3DS-4.png">
        <img src="docs/images/3DS-4.png" width="100%" alt="Puzzle selection screen">
      </a>
    </td>
    <td width="50%">
      <a href="docs/images/3DS-1.png">
        <img src="docs/images/3DS-1.png" width="100%" alt="PictoPlus loader">
      </a>
    </td>
  </tr>
</table>

</details>

## What can you do?

| | |
| --- | --- |
| **Create puzzles** | Build using blue cubes and yellow shapes, either freely or layer by layer. |
| **Import 3D models** | Convert models into puzzles and use textured models for completed reveals. Experimental, but already producing some great results. |
| **Adjust difficulty** | Fine-tune clues for Easy, Medium and Hard, with tools to check whether puzzles can be solved without guessing. |
| **Make puzzle books** | Up to 210 puzzles per book, with custom covers, names and descriptions. |
| **Share your creations** | Export `.pictobook` files for others to play or edit. |
| **Play on 3DS or PC** | Works with Luma3DS and Azahar, with puzzle progress preserved. |

## Download & setup

PictoPlus v1.0.0 supports **USA and EUR** copies of Picross 3D: Round 2.

You'll need Windows 10 (22H2 or newer) or Windows 11 (64-bit), a Nintendo 3DS with Luma3DS or Azahar, and a **legally obtained copy of the game**.

| Download | What it's for |
| --- | --- |
| **[Windows Editor](https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-Windows.zip)** | Create puzzles, import models and build books. |
| **[SD Loader](https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-SD-Loader.zip)** | Play custom books on your 3DS or Azahar. Includes both USA and EUR plugins. |

**Quick setup**

1. Extract the Windows ZIP and run `PictoPlus.exe`.
2. Extract the SD Loader to your 3DS SD card root, or Azahar's virtual `sdmc` folder.
3. Enable **Plugin Loader** in Luma3DS's Rosalina menu (`L + D-Pad Down + Select`), or **3GX Plugin Loader** in Azahar's system settings.
4. Launch the game. For first-time editor setup, import the generated `PictoPlus-Setup.pictosetup` file from your SD card into the Windows app.
5. Export your books and place the `.pictobook` files in `PictoPlus/Books/` on the SD card.

That's it! You can add new books whenever you like without reinstalling the loader.

**[Full installation guide](docs/INSTALLATION.md)** · **[Troubleshooting](docs/TROUBLESHOOTING.md)**

Keep your generated setup file private. It contains resources from your own copy of the game.

## Free Animals Puzzle Pack

<p align="center">
  <a href="https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-Animals-Puzzle-Pack.zip">
    <img src="docs/images/Animals Puzzle Book Banner.png" width="600" alt="Animals Puzzle Pack">
  </a>
</p>

I've also put together a puzzle pack with 30 different animal puzzles, anything from a hummingbird to a hippopotamus. Hopefully the Pug puzzle isn't too difficult!

**[Download the Animals Puzzle Pack](https://github.com/KodakWizard/PictoPlus/releases/download/v1.0.0/PictoPlus-Animals-Puzzle-Pack.zip)**

Extract `Animals.pictobook` into your `PictoPlus/Books/` folder. Replace any older version of the Animals book.

Model credits and CC BY 3.0 licence information are included in the download.

## Community Puzzle Books

Made something you're proud of? I'd love to see it!

You can share your books, download other people's creations and leave feedback over on GitHub Discussions.

**[Browse & submit puzzle books](https://github.com/KodakWizard/PictoPlus/discussions/categories/puzzle-book-submissions)**

To share a book, start a new discussion, attach a ZIP containing your `.pictobook` file and add a short description or screenshots.

Please only share models and artwork you have permission to distribute. Don't share setup files, extracted game resources or save data.

## Help & contributing

Found a bug or have an idea for PictoPlus? Feel free to [open an issue](https://github.com/KodakWizard/PictoPlus/issues).

- [Installation guide](docs/INSTALLATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Previous releases](https://github.com/KodakWizard/PictoPlus/releases)

<details>
<summary><strong>A note on AI</strong></summary>

PictoPlus was developed over the course of a month, with countless hours spent building, refining, debugging and testing it.

AI-assisted coding tools have been a big part of the development process, but this wasn't something that came together with a single prompt. There's been a lot of back and forth, plenty of experimentation, more than a few things breaking, and many rounds of testing to get everything working.

I wanted to be transparent about how it was made, while also acknowledging the time, care and hands-on work that went into it.

</details>

<details>
<summary><strong>Licence and acknowledgements</strong></summary>

PictoPlus's original code is available under the [MIT licence](LICENSE). Third-party dependencies retain their own licences. See [third-party and artwork notices](docs/ASSETS-AND-LICENCES.md).

The cube mascot was generated with ChatGPT, and the built-in covers were made using image-generation tools. AI-generated artwork is not automatically guaranteed to be copyright-free or legally cleared.

PictoPlus is an unofficial fan project and is not affiliated with, sponsored by or endorsed by Nintendo. Nintendo and Picross 3D: Round 2 names and trademarks belong to their respective owners.

**PictoPlus requires a legally obtained copy of Picross 3D: Round 2.** No Nintendo game files, ROMs or proprietary game assets are included in the downloads.

</details>

---

USA gameplay has been tested on a physical 3DS. Both USA and EUR loaders have booted in Azahar. Physical EUR testing is still pending.
