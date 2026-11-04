
<p align="center">
  <img src="docs/images/icon-128.png" width="96" height="96" alt="PictoPlus mascot">
</p>

<h1 align="center">PictoPlus</h1>

<p align="center">
  <strong>Make your own puzzles for Picross 3D: Round 2.</strong>
</p>

Ever wished Picross 3D: Round 2 had more puzzles to play?

PictoPlus lets you create your own 3D puzzles, collect them into books and play them on your Nintendo 3DS. Build something from scratch, experiment with 3D models, or share your creations with friends.

It's a little fan-made project for anyone who loves the game and wants to keep creating.

**v0.9 Beta** · [Download for Windows](https://github.com/KodakWizard/PictoPlus/releases/download/v0.9.0/PictoPlus-Windows-USA.zip) · [USA SD Loader](https://github.com/KodakWizard/PictoPlus/releases/download/v0.9.0/PictoPlus-USA-SD-Loader.zip) · [Release notes](https://github.com/KodakWizard/PictoPlus/releases/tag/v0.9.0)

## A look inside PictoPlus

<table>
  <tr>
    <td width="50%" align="center">
      <a href="docs/images/PictoPlusApp-1.png">
        <img src="docs/images/PictoPlusApp-1.png" width="100%" alt="PictoPlus puzzle designer">
      </a>
      <sub>Build your own puzzles</sub>
    </td>
    <td width="50%" align="center">
      <a href="docs/images/PictoPlusApp-2.png">
        <img src="docs/images/PictoPlusApp-2.png" width="100%" alt="PictoPlus 3D model preview">
      </a>
      <sub>Preview the finished model</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <a href="docs/images/PictoPlusApp-3.png">
        <img src="docs/images/PictoPlusApp-3.png" width="100%" alt="PictoPlus difficulty editor">
      </a>
      <sub>Fine-tune your puzzle's difficulty</sub>
    </td>
    <td width="50%" align="center">
      <a href="docs/images/PictoPlusApp-4.png">
        <img src="docs/images/PictoPlusApp-4.png" width="100%" alt="PictoPlus book library">
      </a>
      <sub>Collect your creations into books</sub>
    </td>
  </tr>
</table>

## Features

- **Create your own 3D puzzles** - Build with blue cubes and yellow shapes, working freely in 3D or one layer at a time.
- **Import 3D models** - Convert existing models into puzzles or attach them as the finished reveal. Conversion is experimental, so some manual editing may be needed.
- **Customise the difficulty** - Preview and fine-tune clues for Easy, Medium and Hard, with tools to check whether puzzles can be solved without guessing.
- **Make your own puzzle books** - Organise up to 210 puzzles per book, with custom covers, artwork, names and descriptions.
- **Play on your 3DS** - Export your books and play them in Picross 3D: Round 2 using the PictoPlus loader.
- **Share your puzzles** - Send `.pictobook` files to friends so they can play your creations or import them into PictoPlus to edit.
- **Keep your progress** - The loader saves your progress and avoids rebuilding books that haven't changed.

## Getting started

You'll need a Windows PC, a Nintendo 3DS with Luma3DS and its plugin loader enabled, and your own installed **USA copy of Picross 3D: Round 2**.

**1. Download PictoPlus**

Download the [Windows app](https://github.com/KodakWizard/PictoPlus/releases/download/v0.9.0/PictoPlus-Windows-USA.zip), extract the entire ZIP and open `PictoPlus.exe`.

**2. Install the 3DS loader**

Download the [USA SD Loader](https://github.com/KodakWizard/PictoPlus/releases/download/v0.9.0/PictoPlus-USA-SD-Loader.zip) and copy its `luma` and `PictoPlus` folders to the root of your SD card.

Enable Luma's plugin loader and launch the installed game. PictoPlus will generate a setup file from your game if one is missing.

**3. Finish setting up the app**

Return your SD card to your computer. In PictoPlus, import:

`SD:/PictoPlus/PictoPlus-Setup.pictosetup`

Already have a valid setup file? You can reuse it without generating another.

Keep this file private, as it contains resources from your installed game.

**4. Create and play!**

Make a puzzle, add it to a book and choose **Export / install** from Book Library.

Copy the exported `.pictobook` file to:

`SD:/PictoPlus/Books/`

Put the SD card back into your 3DS, launch the game and enjoy!

For more information, including reinstalling the loader, skipping setup-file generation, Windows updates and troubleshooting:

[Full installation guide](docs/INSTALLATION.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

**Compatibility:** The public loader currently supports the USA version of the game. EUR development is separate.

## A book to get you started

<img src="docs/images/animals-cover.png" width="180" alt="Animals Puzzle Pack cover">

Not sure where to start? I've put together an **Animals Puzzle Pack** with 15 puzzles, featuring everything from a hummingbird to a hippopotamus.

It's a nice way to try PictoPlus without having to make your own puzzles first.

[**Download the Animals Puzzle Pack**](https://github.com/KodakWizard/PictoPlus/releases/download/v0.9.0/PictoPlus-Animals-Puzzle-Pack.zip)

Just unzip the download and copy `Animals.pictobook` into `SD:/PictoPlus/Books/`. If you already have an older copy of Animals, replace it with the new one.

The pack includes model credits and CC BY 3.0 licence information.

## Sharing your creations

Made something you're proud of?

Share the `.pictobook` file with another PictoPlus user. They can play it directly on their 3DS or import it into the desktop app to make their own changes.

Please only share models and artwork you have permission to distribute. Setup files, game resources and save data should stay private.

## Help & contributing

PictoPlus is still in beta, so there may be a few rough edges.

If you run into a problem or have an idea for something you'd like to see, feel free to [open an issue](https://github.com/KodakWizard/PictoPlus/issues).

Bug reports, suggestions and code contributions are welcome.

If you're interested in contributing, have a look at [CONTRIBUTING.md](CONTRIBUTING.md). You can also follow development in the [changelog](CHANGELOG.md).

## A note on AI

PictoPlus was developed over the course of a month, with countless hours spent building, refining, debugging and testing it.

AI-assisted coding tools have been a big part of the development process, but this wasn't something that came together with a single prompt. There's been a lot of back and forth, plenty of experimentation, more than a few things breaking, and many rounds of testing to get everything working.

I wanted to be transparent about how it was made, while also acknowledging the time, care and hands-on work that went into it.

## Licence and acknowledgements

PictoPlus's original code is available under the [MIT licence](LICENSE). Third-party dependencies retain their own licences. See [third-party and artwork notices](docs/ASSETS-AND-LICENCES.md).

The cube mascot was generated with ChatGPT, and the built-in covers were made using image-generation tools. AI-generated artwork is not automatically guaranteed to be copyright-free or legally cleared.

PictoPlus is an unofficial fan project and is not affiliated with, sponsored by or endorsed by Nintendo. Nintendo and Picross 3D: Round 2 names and trademarks belong to their respective owners.

You'll need your own legitimate copy of the game. PictoPlus does not distribute Nintendo game assets or ROMs.
