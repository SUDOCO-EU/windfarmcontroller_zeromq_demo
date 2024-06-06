conda activate rosco-env
python plot_simulation.py
rm -f output.mp4
ffmpeg -framerate 10 -i flow_visualization/%04d.png -r 25 -c:v libx264 -pix_fmt yuv420p output.mp4
