# Rebuild Main_structure.pptx via PowerPoint COM
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$media = Join-Path $root '_pptx_extract\ppt\media'
$outPath = Join-Path $root 'Main_structure.pptx'
$backup = Join-Path $root 'Main_structure_backup.pptx'

if (Test-Path $outPath) {
    Copy-Item $outPath $backup -Force
}

$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue
$pres = $pp.Presentations.Add()
$pres.PageSetup.SlideWidth = 12192000 / 914400 * 72   # keep default widescreen if possible
try { $pres.PageSetup.SlideSize = 15 } catch {}  # ppSlideSizeOnScreen16x9 = 15

function Add-TitleSlide($title, $subtitle) {
    $s = $pres.Slides.Add($pres.Slides.Count + 1, 1) # ppLayoutTitle
    $s.Shapes.Title.TextFrame.TextRange.Text = $title
    if ($s.Shapes.Count -ge 2 -and $subtitle) {
        $s.Shapes.Item(2).TextFrame.TextRange.Text = $subtitle
    }
    return $s
}

function Add-ContentSlide($title, $bullets, $imagePath = $null) {
    $layout = 2 # ppLayoutText
    if ($imagePath -and (Test-Path $imagePath)) { $layout = 12 } # Title + content often; use blank+manual if needed
    $s = $pres.Slides.Add($pres.Slides.Count + 1, 2) # ppLayoutText
    $s.Shapes.Title.TextFrame.TextRange.Text = $title
    $body = $null
    foreach ($sh in $s.Shapes) {
        if ($sh.HasTextFrame -and -not $sh.Name.ToLower().Contains('title') -and $sh.PlaceholderFormat.Type -ne 1) {
            try {
                if ($sh.PlaceholderFormat.Type -eq 2 -or $sh.PlaceholderFormat.Type -eq 7) {
                    $body = $sh
                    break
                }
            } catch {}
        }
    }
    if (-not $body) {
        foreach ($sh in $s.Shapes) {
            if ($sh.HasTextFrame -and $sh.Id -ne $s.Shapes.Title.Id) { $body = $sh; break }
        }
    }
    if ($body -and $bullets) {
        $body.TextFrame.TextRange.Text = ($bullets -join "`r")
    }
    if ($imagePath -and (Test-Path $imagePath)) {
        # place image on right half
        $null = $s.Shapes.AddPicture($imagePath, $false, $true, 380, 90, 320, 240)
    }
    return $s
}

function Add-ImageSlide($title, $imagePaths, $caption = $null) {
    $s = $pres.Slides.Add($pres.Slides.Count + 1, 2)
    $s.Shapes.Title.TextFrame.TextRange.Text = $title
    # clear body bullets if present
    foreach ($sh in @($s.Shapes)) {
        try {
            if ($sh.HasTextFrame -and $sh.Id -ne $s.Shapes.Title.Id) {
                $sh.TextFrame.TextRange.Text = $(if ($caption) { $caption } else { '' })
            }
        } catch {}
    }
    $n = $imagePaths.Count
    $i = 0
    foreach ($p in $imagePaths) {
        if (-not (Test-Path $p)) { continue }
        $w = [Math]::Min(280, 640 / [Math]::Max($n,1))
        $x = 40 + $i * ($w + 20)
        $null = $s.Shapes.AddPicture($p, $false, $true, $x, 100, $w, 260)
        $i++
    }
    return $s
}

# ---- Slides ----
Add-TitleSlide 'Quantum Simulation: Adiabatic Hamiltonian' 'Ground states, Ising paths, and digital adiabatic methods' | Out-Null

Add-ContentSlide 'Contents' @(
    '1. Introduction and roadmap',
    '2. Algorithms and layers',
    '3. From physics to Hamiltonians',
    '4. Static vs dynamic; ground-state problems',
    '5. Adiabatic computation',
    '6. Worked example: 2-qubit Ising',
    '7. Qiskit implementation',
    '8. Gap, scheduling, and required time',
    '9. Complexity and scaling',
    '10. Challenges and summary'
) | Out-Null

Add-ContentSlide 'Motivation' @(
    'Quantum simulation turns a physical model into a computational task',
    'Shared language: algorithms, Hamiltonians, methods',
    'Focus: adiabatic paths for ground-state problems',
    'Worked Ising example + Qiskit for intuition'
) | Out-Null

Add-ContentSlide 'Roadmap' @(
    'Algorithms -> Physics to H -> Static/dynamic',
    '-> Adiabatic path -> Ising example -> Qiskit',
    '-> Gap and T -> Complexity',
    'Deep dive on adiabatic ground-state computation'
) | Out-Null

Add-ContentSlide 'Three Layers' @(
    'Algorithm: research question',
    'Simulation: model and Hamiltonian H',
    'Tools: Trotter, adiabatic, VQE, ...',
    'Path: question -> H -> method'
) | Out-Null

Add-ContentSlide 'From Physics to Hamiltonian' @(
    'Physical problem -> idealized model',
    'Keep degrees of freedom -> Hamiltonian H',
    'Then choose the question: static vs dynamic',
    'Fix H before choosing a method'
) | Out-Null

Add-ContentSlide 'Dynamics or Statics?' @(
    'Dynamics: U(t)=exp(-iHt); quench, transport',
    'Static / spectral: ground state, gap, eigenvalues',
    'This talk follows the static / ground-state branch'
) (Join-Path $media 'image1.png') | Out-Null

Add-ContentSlide 'Ground-State Problems' @(
    'Lowest-energy configuration of physical models',
    'Many optimization tasks map to Ising / QUBO',
    'Gap and low-lying spectrum control physics and runtime',
    'Target: ground state of a problem Hamiltonian H_P'
) | Out-Null

Add-ContentSlide 'Adiabatic Idea' @(
    'Start from easy initial Hamiltonian H_init (H_B)',
    'Interpolate slowly to problem Hamiltonian H_P',
    'Sufficient gap and time => ground state of H_P'
) | Out-Null

Add-ImageSlide 'The Path H(s)' @(
    (Join-Path $media 'image2.png'),
    (Join-Path $media 'image4.png')
) 'H(s)=(1-s)H_init + s H_problem; example schedule s(t)=t/T' | Out-Null

Add-ImageSlide 'Minimum Gap Controls Runtime' @(
    (Join-Path $media 'image3.png'),
    (Join-Path $media 'image5.png')
) 'Delta(s)=E1-E0; bottleneck Delta_min; heuristic T ~ 1/Delta_min^2' | Out-Null

Add-ImageSlide 'Example: Initial and Problem Hamiltonians' @(
    (Join-Path $media 'image6.png'),
    (Join-Path $media 'image7.png'),
    (Join-Path $media 'image8.png')
) 'Initial H_B (driver/beginning); problem H_P for 2-qubit Ising' | Out-Null

Add-ImageSlide 'Adiabatic Pipeline for Ising' @(
    (Join-Path $media 'image9.png')
) 'H_B, |++> -> H(s) -> Delta_min ~ 0.66 at s* ~ 0.62 -> readout |00>' | Out-Null

Add-ContentSlide 'Qiskit: Role' @(
    'Shared stack for digital circuits',
    'Turns the adiabatic path into a reproducible workflow',
    'Environment: conda activate qcomputing'
) | Out-Null

Add-ImageSlide 'Qiskit: Build H(s)' @(
    (Join-Path $media 'image11.png')
) 'SparsePauliOp: define H_B, H_P, and linear path H(s)' | Out-Null

Add-ImageSlide 'Qiskit: Trotter Layer and Gap Plot' @(
    (Join-Path $media 'image12.png'),
    (Join-Path $media 'image10.png')
) 'Hadamard prep, Trotter layers R_x / R_zz / R_z, Z readout; scan Delta(s)' | Out-Null

Add-ContentSlide 'Gap Vocabulary' @(
    'Instantaneous gap: Delta(s) = E1(s) - E0(s)',
    'Minimum gap: Delta_min = min_s Delta(s) --- bottleneck',
    'Avoided crossing: levels approach then separate',
    'Full gap vs gap inside a reachable symmetry sector',
    'Three meanings of required time: heuristic / bound / practical'
) | Out-Null

Add-ImageSlide 'Scheduling: Linear or Nonlinear' @(
    (Join-Path $media 'image17.png'),
    (Join-Path $media 'image18.png')
) 'Same path H(s); slow down near the bottleneck' | Out-Null

Add-ImageSlide 'Scaling with System Size' @(
    (Join-Path $media 'image15.png'),
    (Join-Path $media 'image13.png')
) 'n -> H_n(s) -> Delta_min(n) -> T(n); poly vs exponential closing' | Out-Null

Add-ImageSlide 'Polynomial vs Exponential Runtime' @(
    (Join-Path $media 'image16.png'),
    (Join-Path $media 'image14.png')
) 'T ~ n^(2 alpha) vs T ~ exp(2 c n); qubit count alone is not difficulty' | Out-Null

Add-ContentSlide 'What Limits Adiabatic Simulation' @(
    'Gap closing with system size (poly vs exponential)',
    'Control / scheduling near the bottleneck',
    'Noise and symmetry breaking',
    'Trotter error and circuit depth in digital implementations',
    'Related routes for same H_P: QAOA, VQE'
) | Out-Null

Add-ContentSlide 'Key Takeaways' @(
    'Fix H and degrees of freedom first',
    'Static and dynamic questions are distinct for the same H',
    'Adiabatic computation is a path H(s); the gap sets the time',
    'Complexity follows Delta_min(n), not n alone',
    'Worked Ising + Qiskit make gap and runtime concrete'
) | Out-Null

Add-ContentSlide 'Outlook' @(
    'Adaptive schedules near a small gap',
    'Scaling beyond n=2 (TFIM families)',
    'Compare with QAOA / VQE',
    'Notes: QS&QA_Fundation/QS&QA_Fundation.tex'
) | Out-Null

# Remove the default empty first slide if Presentations.Add created one blank
# PowerPoint often starts with one slide already
if ($pres.Slides.Count -gt 1) {
    # The first slide from Add() is usually a blank title; delete if empty title
    $first = $pres.Slides.Item(1)
    $t = ''
    try { $t = $first.Shapes.Title.TextFrame.TextRange.Text } catch {}
    if ([string]::IsNullOrWhiteSpace($t)) {
        $first.Delete()
    }
}

$nSlides = $pres.Slides.Count
if (Test-Path $outPath) { Remove-Item $outPath -Force }
$pres.SaveAs($outPath)
$pres.Close()
$pp.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
Write-Output "Wrote $outPath with $nSlides slides"
Write-Output 'Done.'
