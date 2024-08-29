from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import pdfkit


def hello():

    c = canvas.Canvas("hello.pdf", pagesize=letter)
    page_width, page_height = letter  # keep for later
    # print(page_width, page_height)

    border = 30
    num_boxes_width = 3
    num_boxes_height = 3
    grid_box_width = (page_width - (border * (num_boxes_width + 1))) / num_boxes_width
    grid_box_height = (page_height - (border * (num_boxes_height + 1))) / num_boxes_height
    print(grid_box_width, grid_box_height)

    # grid_xlist = []
    # border_x = 0
    # box_x = 0
    # for i in range(1, num_boxes_width + 1):
    #     border_i = i + 1
    #     border_x += (border * i)
    #     box_x += (grid_box_width * i) + (border * (i + 1))
    #     grid_xlist.append(border_x)
    #     grid_xlist.append(box_x)
    #
    # grid_ylist = []
    # for i in range(1, num_boxes_height + 1):
    #     grid_ylist.append(border * i)
    #     grid_ylist.append((grid_box_height * i) + border * i)
    #
    # print(grid_xlist)
    # print(grid_ylist)

    rectangle_coords = [
        (30, 538), (224, 538), (418, 538),
        (30, 284), (224, 284), (418, 284),
        (30, 30), (224, 30), (418, 30),
    ]

    for r in rectangle_coords:
        c.rect(r[0], r[1], grid_box_width, grid_box_height, stroke=1, fill=0)

    c.drawString(100, 100, "Hello World")
    # c.grid(xlist=grid_xlist, ylist=grid_ylist)
    return c


def pdfkit_example():
    options = {
        'page-size': 'Letter',
        'margin-top': None,
        'margin-right': None,
        'margin-bottom': None,
        'margin-left': None,
        'encoding': "UTF-8",
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'no-outline': None
    }
    pdfkit.from_file(['file1.html', 'file2.html'], 'out.pdf', options=options)


def main():
    ...
    # get all obs > input ID number
    # filter by kingdom/taxon (ex: fungi)
    # get recent inat observation info (ID, location, datetime, etc)
    # if obscured, leave location/datetime blank
    # include species? or leave blank to be filled in?
    # format as PDF
    # download/save to print

    c = hello()
    c.showPage()
    c.save()


if __name__ == '__main__':
    main()
